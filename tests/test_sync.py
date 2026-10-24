from datetime import datetime

import pytest

import src.downloader as downloader
import src.sync_raw_files as sync_raw_files

OLD = "2026-05-01T10:00:00"
SITE_OLD = datetime(2026, 5, 1, 10)
SITE_NEW = datetime(2026, 6, 1, 10)


def make_entry(name, last_site_date=OLD, last_system_date="2026-01-01T00:00:00"):
    return {
        "nome_tabela": name,
        "tipo_arquivo": "csv",
        "link": "http://exemplo/arquivo.csv",
        "data_ultima_atualizacao_site": last_site_date,
        "data_atualizacao_sistema": last_system_date,
    }


@pytest.fixture
def bronze(monkeypatch, tmp_path):
    """Bronze falso: controla quais blobs existem e registra uploads."""
    state = {"existing": set(), "uploaded": [], "saved_manifests": []}
    monkeypatch.setattr(downloader, "blob_exists", lambda container, name, s: name in state["existing"])
    monkeypatch.setattr(downloader, "get_work_path", lambda relative, s: tmp_path / relative)

    def fake_download(url, destination, s):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("a;b\n1;2\n")
        return destination

    monkeypatch.setattr(downloader, "download_to_local", fake_download)
    monkeypatch.setattr(downloader, "upload_file", lambda path, container, name, s: state["uploaded"].append(name))
    monkeypatch.setattr(sync_raw_files, "save_manifest_entries", lambda entries, s: state["saved_manifests"].append(list(entries)))
    return state


def test_downloads_when_blob_is_missing(bronze, settings):
    needed, reason = downloader.decide_sync_action(make_entry("a"), SITE_OLD, settings)
    assert needed is True and "ausente" in reason


def test_skips_when_site_date_is_unchanged(bronze, settings):
    bronze["existing"].add("a.csv")
    needed, reason = downloader.decide_sync_action(make_entry("a"), SITE_OLD, settings)
    assert needed is False and "sem mudanca" in reason


def test_downloads_when_site_published_newer_data(bronze, settings):
    bronze["existing"].add("a.csv")
    needed, reason = downloader.decide_sync_action(make_entry("a"), SITE_NEW, settings)
    assert needed is True and "site atualizado" in reason


def test_keeps_current_bronze_when_site_date_cannot_be_read(bronze, settings):
    bronze["existing"].add("a.csv")
    needed, reason = downloader.decide_sync_action(make_entry("a"), None, settings)
    assert needed is False and "indisponivel" in reason


def test_downloads_even_without_site_date_if_bronze_is_empty(bronze, settings):
    needed, _ = downloader.decide_sync_action(make_entry("a"), None, settings)
    assert needed is True


def test_sync_all_only_uploads_what_changed(bronze, settings, monkeypatch):
    bronze["existing"].update({"a.csv", "b.csv", "c.csv"})          # e.csv nao existe
    site_dates = {"a": SITE_OLD, "b": SITE_NEW, "c": None, "e": SITE_OLD}
    monkeypatch.setattr(sync_raw_files, "fetch_current_site_date", lambda entry, s: site_dates[entry["nome_tabela"]])

    entries = [make_entry(name) for name in "abce"]
    updated = {e["nome_tabela"]: e for e in sync_raw_files.sync_all_entries(entries, settings)}

    assert bronze["uploaded"] == ["b.csv", "e.csv"]
    assert updated["b"]["data_ultima_atualizacao_site"] == "2026-06-01T10:00:00"
    # o relogio antigo do sistema NAO fez "a" ser baixado de novo
    assert updated["a"]["data_atualizacao_sistema"] == "2026-01-01T00:00:00"


def test_manifest_is_saved_after_each_upload_so_progress_survives_a_crash(bronze, settings, monkeypatch):
    site_dates = {"a": SITE_OLD, "b": SITE_OLD, "c": SITE_OLD}
    monkeypatch.setattr(sync_raw_files, "fetch_current_site_date", lambda entry, s: site_dates[entry["nome_tabela"]])

    def upload_that_fails_on_c(path, container, name, s):
        if name == "c.csv":
            raise TimeoutError("simulado")
        bronze["uploaded"].append(name)

    monkeypatch.setattr(downloader, "upload_file", upload_that_fails_on_c)

    with pytest.raises(TimeoutError):
        sync_raw_files.sync_all_entries([make_entry(n) for n in "abc"], settings)

    last_saved = {e["nome_tabela"]: e for e in bronze["saved_manifests"][-1]}
    assert last_saved["a"]["data_atualizacao_sistema"] != "2026-01-01T00:00:00"
    assert last_saved["b"]["data_atualizacao_sistema"] != "2026-01-01T00:00:00"
    assert last_saved["c"]["data_atualizacao_sistema"] == "2026-01-01T00:00:00"   # falhou: continua pendente


def test_fetch_current_site_date_handles_missing_page_and_scrape_errors(settings, monkeypatch):
    assert sync_raw_files.fetch_current_site_date({"nome_tabela": "a"}, settings) is None

    def broken(url, s):
        raise ConnectionError("fora do ar")

    monkeypatch.setattr(sync_raw_files, "fetch_site_last_update", broken)
    assert sync_raw_files.fetch_current_site_date({"nome_tabela": "a", "pagina_dataset": "http://x"}, settings) is None
