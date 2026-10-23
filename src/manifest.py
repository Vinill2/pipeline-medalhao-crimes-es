import json
from datetime import datetime

from src.settings import get_project_path, load_json_file


def get_manifest_entries(settings: dict) -> list:
    manifest_path = get_project_path(settings["paths"]["manifest"])
    manifest_entries = load_json_file(manifest_path)
    return manifest_entries


def save_manifest_entries(entries: list, settings: dict) -> None:
    manifest_path = get_project_path(settings["paths"]["manifest"])
    with open(manifest_path, "w", encoding="utf-8") as manifest_file:
        json.dump(entries, manifest_file, ensure_ascii=False, indent=2)


def parse_manifest_date(date_text: str) -> datetime:
    parsed_date = datetime.fromisoformat(date_text)
    return parsed_date


def has_site_update(entry: dict, site_date: datetime) -> bool:
    # O criterio e a data que esta NO SITE agora (site_date, raspada na hora)
    # contra a ultima data do site que ja foi sincronizada com sucesso (guardada
    # no manifesto). Nao depende do relogio da maquina que roda o pipeline.
    last_synced_site_date_text = entry.get("data_ultima_atualizacao_site")
    if not last_synced_site_date_text:
        return True
    last_synced_site_date = parse_manifest_date(last_synced_site_date_text)
    site_has_update = site_date != last_synced_site_date
    return site_has_update


def mark_entry_as_synced(entry: dict, site_date: datetime = None) -> dict:
    # Chamada so depois de um download + upload bem sucedido: e aqui que a data do
    # site passa a valer como "ja sincronizada". Se o download falhar, o manifesto
    # fica como estava e a proxima execucao tenta de novo.
    synced_entry = dict(entry)
    synced_entry["data_atualizacao_sistema"] = datetime.now().isoformat(timespec="seconds")
    if site_date is not None:
        synced_entry["data_ultima_atualizacao_site"] = site_date.isoformat(timespec="seconds")
    return synced_entry
