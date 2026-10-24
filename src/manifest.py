import json
from datetime import datetime

from src.azure_storage import get_work_path, try_download_file, upload_file
from src.settings import get_project_path, load_json_file

# Campos de ESTADO: mudam a cada execucao e por isso ficam no Azure, nao no Git.
# O config/sources.json do repositorio guarda so a configuracao (nome, link, pagina...)
# e, no maximo, o valor inicial desses campos. Assim o pipeline nao precisa dar
# commit no repositorio (o que impediria proteger o ramo main).
STATE_FIELDS = ("data_ultima_atualizacao_site", "data_atualizacao_sistema")
DEFAULT_STATE_BLOB_NAME = "_state/manifest_state.json"


def get_state_blob_name(settings: dict) -> str:
    return settings["azure"].get("state_blob_name", DEFAULT_STATE_BLOB_NAME)


def load_remote_state(settings: dict) -> dict:
    """Estado salvo no Azure (por nome_tabela), ou {} se ainda nao existe (primeira execucao)."""
    local_path = get_work_path("manifest_state.json", settings)
    container_name = settings["azure"]["bronze_container"]
    was_downloaded = try_download_file(container_name, get_state_blob_name(settings), local_path, settings)
    if not was_downloaded:
        return {}
    return load_json_file(local_path)


def merge_state_into_entry(entry: dict, entry_state: dict) -> dict:
    merged_entry = dict(entry)
    for field_name in STATE_FIELDS:
        if field_name in entry_state:
            merged_entry[field_name] = entry_state[field_name]
    return merged_entry


def get_manifest_entries(settings: dict) -> list:
    manifest_path = get_project_path(settings["paths"]["manifest"])
    configured_entries = load_json_file(manifest_path)
    remote_state = load_remote_state(settings)
    return [merge_state_into_entry(entry, remote_state.get(entry["nome_tabela"], {})) for entry in configured_entries]


def save_manifest_entries(entries: list, settings: dict) -> None:
    state_by_table = {
        entry["nome_tabela"]: {field_name: entry[field_name] for field_name in STATE_FIELDS if field_name in entry}
        for entry in entries
    }
    local_path = get_work_path("manifest_state.json", settings)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, "w", encoding="utf-8") as state_file:
        json.dump(state_by_table, state_file, ensure_ascii=False, indent=2)
    upload_file(local_path, settings["azure"]["bronze_container"], get_state_blob_name(settings), settings)


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
