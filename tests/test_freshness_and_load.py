from datetime import datetime, timezone

import pytest

import src.load_silver_staging as load_silver_staging
from src.freshness import is_derived_up_to_date


def at(hour):
    return datetime(2026, 10, 21, hour, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "source, derived, expected",
    [
        (at(8), at(9), True),      # derivado e mais novo
        (at(8), at(8), True),      # iguais contam como em dia
        (at(9), at(8), False),     # origem mudou depois
        (None, at(9), False),      # origem sumiu
        (at(8), None, False),      # derivado nao existe
        (None, None, False),
    ],
)
def test_is_derived_up_to_date(source, derived, expected):
    assert is_derived_up_to_date(source, derived) is expected


@pytest.fixture
def azure_dates(monkeypatch):
    dates = {}
    monkeypatch.setattr(load_silver_staging, "get_blob_last_modified", lambda container, blob, s: dates.get((container, blob)))
    monkeypatch.setattr(load_silver_staging, "get_bronze_blob_name", lambda entry: f"{entry['nome_tabela']}.csv")
    return dates


def set_dates(dates, settings, bronze, staging):
    dates.clear()
    for name in bronze:
        dates[(settings["azure"]["bronze_container"], f"{name}.csv")] = bronze[name]
    for name in staging:
        blob = load_silver_staging.get_staging_blob_name({"nome_tabela": name}, settings)
        dates[(settings["azure"]["silver_container"], blob)] = staging[name]


ENTRIES = [{"nome_tabela": name} for name in ("a", "b", "c")]


def test_only_datasets_with_newer_bronze_need_loading(azure_dates, settings):
    set_dates(azure_dates, settings, {"a": at(8), "b": at(11), "c": at(8)}, {"a": at(9), "b": at(9), "c": at(9)})
    pending = load_silver_staging.get_entries_to_load(ENTRIES, settings)
    assert [e["nome_tabela"] for e in pending] == ["b"]


def test_missing_staging_file_needs_loading(azure_dates, settings):
    set_dates(azure_dates, settings, {"a": at(8), "b": at(8), "c": at(8)}, {"a": at(9), "b": at(9)})
    pending = load_silver_staging.get_entries_to_load(ENTRIES, settings)
    assert [e["nome_tabela"] for e in pending] == ["c"]


def test_force_loads_everything_without_checking_azure(azure_dates, settings):
    set_dates(azure_dates, settings, {"a": at(8), "b": at(8), "c": at(8)}, {"a": at(9), "b": at(9), "c": at(9)})
    assert len(load_silver_staging.get_entries_to_load(ENTRIES, settings, force=True)) == 3


def test_load_all_entries_skips_up_to_date_and_reports_failures(azure_dates, settings, monkeypatch):
    set_dates(azure_dates, settings, {"a": at(8), "b": at(11), "c": at(11)}, {"a": at(9), "b": at(9), "c": at(9)})

    def fake_load(entry, s):
        if entry["nome_tabela"] == "c":
            raise RuntimeError("csv quebrado")
        return 42

    monkeypatch.setattr(load_silver_staging, "load_entry_to_silver", fake_load)
    summary = load_silver_staging.load_all_entries(ENTRIES, settings)

    assert summary["skipped"] == ["a"]
    assert summary["loaded"] == {"b": 42}
    assert list(summary["failed"]) == ["c"]
    assert "csv quebrado" in summary["failed"]["c"]


def test_staging_blob_name_follows_prefix_convention(settings):
    blob = load_silver_staging.get_staging_blob_name({"nome_tabela": "roubo_celular"}, settings)
    assert blob == f"{settings['azure']['silver_staging_prefix']}/stg_roubo_celular.parquet"
