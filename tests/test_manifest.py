import json
from datetime import datetime

import pytest

import src.manifest as manifest
from src.manifest import has_site_update, mark_entry_as_synced, merge_state_into_entry

SITE_DATE = datetime(2026, 6, 1, 10, 0, 0)


def test_has_update_when_never_synced():
    assert has_site_update({}, SITE_DATE) is True


def test_no_update_when_site_date_equals_last_synced():
    assert has_site_update({"data_ultima_atualizacao_site": "2026-06-01T10:00:00"}, SITE_DATE) is False


def test_update_when_site_date_changed():
    assert has_site_update({"data_ultima_atualizacao_site": "2026-05-01T10:00:00"}, SITE_DATE) is True


def test_system_clock_is_irrelevant_to_the_decision():
    # data_atualizacao_sistema bem recente NAO pode esconder uma atualizacao do site
    entry = {"data_ultima_atualizacao_site": "2026-05-01T10:00:00", "data_atualizacao_sistema": "2030-01-01T00:00:00"}
    assert has_site_update(entry, SITE_DATE) is True


def test_mark_as_synced_records_site_date_and_leaves_input_untouched():
    entry = {"nome_tabela": "a", "data_ultima_atualizacao_site": "2020-01-01T00:00:00"}
    synced = mark_entry_as_synced(entry, SITE_DATE)
    assert synced["data_ultima_atualizacao_site"] == "2026-06-01T10:00:00"
    assert datetime.fromisoformat(synced["data_atualizacao_sistema"])
    assert entry["data_ultima_atualizacao_site"] == "2020-01-01T00:00:00"


def test_mark_as_synced_without_site_date_keeps_stored_site_date():
    entry = {"nome_tabela": "a", "data_ultima_atualizacao_site": "2020-01-01T00:00:00"}
    assert mark_entry_as_synced(entry)["data_ultima_atualizacao_site"] == "2020-01-01T00:00:00"


def test_merge_state_overrides_only_state_fields():
    entry = {"nome_tabela": "a", "link": "u", "data_ultima_atualizacao_site": "old"}
    merged = merge_state_into_entry(entry, {"data_ultima_atualizacao_site": "new", "link": "HACK"})
    assert merged == {"nome_tabela": "a", "link": "u", "data_ultima_atualizacao_site": "new"}


@pytest.fixture
def fake_azure(tmp_path, monkeypatch, settings):
    """Troca o Azure por um dicionario em memoria e o projeto por uma pasta temporaria."""
    config_path = tmp_path / "config" / "sources.json"
    config_path.parent.mkdir()
    seed = [
        {"nome_tabela": "a", "link": "u1", "data_ultima_atualizacao_site": "2026-01-01T00:00:00"},
        {"nome_tabela": "b", "link": "u2"},
    ]
    config_path.write_text(json.dumps(seed), encoding="utf-8")

    remote_blobs = {}
    monkeypatch.setattr(manifest, "get_project_path", lambda relative: tmp_path / relative)
    monkeypatch.setattr(manifest, "get_work_path", lambda relative, s: tmp_path / "work" / relative)

    def fake_try_download(container, blob, local_path, s):
        if (container, blob) not in remote_blobs:
            return False
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(remote_blobs[(container, blob)], encoding="utf-8")
        return True

    def fake_upload(local_path, container, blob, s):
        remote_blobs[(container, blob)] = local_path.read_text(encoding="utf-8")

    monkeypatch.setattr(manifest, "try_download_file", fake_try_download)
    monkeypatch.setattr(manifest, "upload_file", fake_upload)
    return {"config_path": config_path, "remote": remote_blobs, "settings": settings, "seed": seed}


def test_first_run_uses_seed_from_repository_file(fake_azure):
    entries = manifest.get_manifest_entries(fake_azure["settings"])
    assert entries[0]["data_ultima_atualizacao_site"] == "2026-01-01T00:00:00"
    assert "data_ultima_atualizacao_site" not in entries[1]


def test_state_roundtrip_goes_to_azure_and_overrides_seed(fake_azure):
    settings = fake_azure["settings"]
    entries = manifest.get_manifest_entries(settings)
    entries[0] = mark_entry_as_synced(entries[0], SITE_DATE)
    manifest.save_manifest_entries(entries, settings)

    assert (settings["azure"]["bronze_container"], "_state/manifest_state.json") in fake_azure["remote"]
    reloaded = manifest.get_manifest_entries(settings)
    assert reloaded[0]["data_ultima_atualizacao_site"] == "2026-06-01T10:00:00"


def test_saving_state_never_rewrites_the_repository_config_file(fake_azure):
    settings = fake_azure["settings"]
    before = fake_azure["config_path"].read_text(encoding="utf-8")
    entries = manifest.get_manifest_entries(settings)
    manifest.save_manifest_entries([mark_entry_as_synced(e, SITE_DATE) for e in entries], settings)
    assert fake_azure["config_path"].read_text(encoding="utf-8") == before


def test_new_dataset_added_to_config_has_no_remote_state(fake_azure):
    settings = fake_azure["settings"]
    manifest.save_manifest_entries(manifest.get_manifest_entries(settings), settings)
    fake_azure["config_path"].write_text(
        json.dumps(fake_azure["seed"] + [{"nome_tabela": "novo", "link": "u3"}]), encoding="utf-8"
    )
    entries = {e["nome_tabela"]: e for e in manifest.get_manifest_entries(settings)}
    assert "data_ultima_atualizacao_site" not in entries["novo"]
    assert has_site_update(entries["novo"], SITE_DATE) is True
