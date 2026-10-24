from datetime import datetime, timezone

import pytest

import src.load_silver_staging as load_silver_staging
import src.pipeline as pipeline

ENTRIES = [{"nome_tabela": name} for name in ("a", "b", "c")]


def at(hour):
    return datetime(2026, 10, 21, hour, tzinfo=timezone.utc)


@pytest.fixture
def flow(monkeypatch, settings):
    """Pipeline com todas as etapas trocadas por espioes; datas do Azure controlaveis."""
    flow = {"dates": {}, "calls": [], "loaded": []}
    monkeypatch.setattr(pipeline, "get_settings", lambda: settings)
    monkeypatch.setattr(pipeline, "get_manifest_entries", lambda s: ENTRIES)
    for module in (load_silver_staging, pipeline):
        monkeypatch.setattr(module, "get_blob_last_modified", lambda container, blob, s: flow["dates"].get((container, blob)))
    monkeypatch.setattr(load_silver_staging, "get_bronze_blob_name", lambda entry: f"{entry['nome_tabela']}.csv")
    monkeypatch.setattr(load_silver_staging, "upload_reference_table", lambda entries, s: None)

    def fake_load_entry(entry, s):
        flow["loaded"].append(entry["nome_tabela"])
        return 10

    monkeypatch.setattr(load_silver_staging, "load_entry_to_silver", fake_load_entry)
    monkeypatch.setattr(pipeline, "run_sync", lambda: flow["calls"].append("sync"))
    monkeypatch.setattr(
        pipeline,
        "run_load",
        lambda force=False, entries_to_load=None: (
            flow["calls"].append("load"),
            load_silver_staging.load_all_entries(ENTRIES, settings, entries_to_load=entries_to_load, force=force),
        )[1],
    )
    monkeypatch.setattr(pipeline, "run_prepare", lambda: flow["calls"].append("prepare"))
    monkeypatch.setattr(pipeline, "run_export", lambda: flow["calls"].append("export"))
    monkeypatch.setattr(pipeline, "run_dbt_command", lambda args: flow["calls"].append(f"dbt {args[0]}"))

    def set_state(bronze, staging, silver_final, gold_fact):
        azure = settings["azure"]
        flow["dates"].clear()
        for name in "abc":
            flow["dates"][(azure["bronze_container"], f"{name}.csv")] = bronze[name]
            blob = load_silver_staging.get_staging_blob_name({"nome_tabela": name}, settings)
            flow["dates"][(azure["silver_container"], blob)] = staging[name]
        flow["dates"][(azure["silver_container"], azure["silver_final_blob_name"])] = silver_final
        flow["dates"][(azure["gold_container"], f"{settings['gold']['fact_table']}.parquet")] = gold_fact

    flow["set_state"] = set_state
    return flow


BRONZE_OK = {name: at(8) for name in "abc"}
STAGING_OK = {name: at(9) for name in "abc"}
FULL_RUN = ["sync", "load", "prepare", "dbt run", "dbt test", "export"]


def test_stops_after_sync_when_nothing_changed(flow):
    flow["set_state"](BRONZE_OK, STAGING_OK, at(10), at(10))
    assert pipeline.run_pipeline() is False
    assert flow["calls"] == ["sync"]


def test_only_changed_dataset_is_reloaded_but_downstream_runs_in_full(flow):
    flow["set_state"](dict(BRONZE_OK, b=at(11)), STAGING_OK, at(10), at(10))
    assert pipeline.run_pipeline() is True
    assert flow["loaded"] == ["b"]
    assert flow["calls"] == FULL_RUN


def test_force_reloads_everything(flow):
    flow["set_state"](BRONZE_OK, STAGING_OK, at(10), at(10))
    pipeline.run_pipeline(force=True)
    assert flow["loaded"] == ["a", "b", "c"]
    assert flow["calls"] == FULL_RUN


def test_self_heals_when_previous_run_died_before_export(flow):
    flow["set_state"](BRONZE_OK, STAGING_OK, at(5), at(5))     # gold mais velha que o stg
    pipeline.run_pipeline()
    assert flow["loaded"] == []                                 # nao regera stg
    assert flow["calls"] == FULL_RUN                            # mas refaz dbt + export


def test_first_run_with_missing_gold_runs_everything(flow, settings):
    flow["set_state"](BRONZE_OK, STAGING_OK, at(10), at(10))
    gold_fact_key = (settings["azure"]["gold_container"], f"{settings['gold']['fact_table']}.parquet")
    del flow["dates"][gold_fact_key]
    assert pipeline.run_pipeline() is True
    assert flow["calls"][-1] == "export"


def test_load_failure_stops_before_dbt(flow, monkeypatch):
    flow["set_state"](dict(BRONZE_OK, b=at(11)), STAGING_OK, at(10), at(10))

    def broken(entry, s):
        raise RuntimeError("csv quebrado")

    monkeypatch.setattr(load_silver_staging, "load_entry_to_silver", broken)
    with pytest.raises(pipeline.PipelineError, match="carga do silver falhou"):
        pipeline.run_pipeline()
    assert "prepare" not in flow["calls"] and "export" not in flow["calls"]


def test_failed_dbt_test_blocks_export(flow, monkeypatch):
    flow["set_state"](dict(BRONZE_OK, b=at(11)), STAGING_OK, at(10), at(10))

    def dbt(args):
        flow["calls"].append(f"dbt {args[0]}")
        if args[0] == "test":
            raise pipeline.PipelineError("dbt test falhou")

    monkeypatch.setattr(pipeline, "run_dbt_command", dbt)
    with pytest.raises(pipeline.PipelineError):
        pipeline.run_pipeline()
    assert "export" not in flow["calls"]


def test_skip_tests_flag_skips_dbt_test_only(flow):
    flow["set_state"](dict(BRONZE_OK, b=at(11)), STAGING_OK, at(10), at(10))
    pipeline.run_pipeline(skip_tests=True)
    assert flow["calls"] == ["sync", "load", "prepare", "dbt run", "export"]
