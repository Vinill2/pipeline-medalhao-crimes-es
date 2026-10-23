import zipfile
from pathlib import Path

import requests

from src.azure_storage import blob_exists, get_work_path, upload_file
from src.manifest import has_site_update


def get_bronze_blob_name(entry: dict) -> str:
    # O blob no bronze e sempre .csv, mesmo quando a origem e um .zip
    # (o zip e so um empacotamento de transporte; o que persiste e o CSV extraido).
    bronze_blob_name = f"{entry['nome_tabela']}.csv"
    return bronze_blob_name


def decide_sync_action(entry: dict, site_date, settings: dict) -> tuple:
    """Devolve (precisa_baixar, motivo). site_date e a data raspada do site agora (ou None)."""
    bronze_blob_name = get_bronze_blob_name(entry)
    container_name = settings["azure"]["bronze_container"]
    if not blob_exists(container_name, bronze_blob_name, settings):
        return True, "arquivo ausente no bronze"
    if site_date is None:
        return False, "data do site indisponivel, mantendo o bronze atual"
    if has_site_update(entry, site_date):
        return True, f"site atualizado ({entry.get('data_ultima_atualizacao_site')} -> {site_date.isoformat(timespec='seconds')})"
    return False, f"site sem mudanca desde {entry['data_ultima_atualizacao_site']}"


def is_zip_file(file_path: Path) -> bool:
    file_is_zip = file_path.suffix.lower() == ".zip"
    return file_is_zip


def download_to_local(url: str, destination: Path, settings: dict) -> Path:
    download_settings = settings["download"]
    partial_path = destination.with_suffix(destination.suffix + ".part")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request_headers = {"User-Agent": download_settings["user_agent"]}
    with requests.get(url, stream=True, headers=request_headers, timeout=download_settings["timeout_seconds"]) as response:
        response.raise_for_status()
        with open(partial_path, "wb") as output_file:
            for chunk in response.iter_content(chunk_size=download_settings["chunk_size_bytes"]):
                output_file.write(chunk)
    partial_path.replace(destination)
    return destination


def get_csv_member_name(zip_file: zipfile.ZipFile) -> str:
    csv_member_names = [name for name in zip_file.namelist() if name.lower().endswith(".csv")]
    first_csv_member_name = csv_member_names[0]
    return first_csv_member_name


def extract_csv_from_zip(zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path) as zip_file:
        member_name = get_csv_member_name(zip_file)
        zip_file.extract(member_name, zip_path.parent)
    extracted_csv_path = zip_path.parent / member_name
    return extracted_csv_path


def sync_raw_file_to_bronze(entry: dict, site_date, settings: dict) -> tuple:
    """Devolve (foi_enviado, motivo)."""
    download_needed, reason = decide_sync_action(entry, site_date, settings)
    if not download_needed:
        return False, reason

    source_file_extension = entry["tipo_arquivo"].lower()
    local_download_path = get_work_path(f"downloads/{entry['nome_tabela']}.{source_file_extension}", settings)
    download_to_local(entry["link"], local_download_path, settings)

    csv_local_path = (
        extract_csv_from_zip(local_download_path) if is_zip_file(local_download_path) else local_download_path
    )

    bronze_blob_name = get_bronze_blob_name(entry)
    container_name = settings["azure"]["bronze_container"]
    upload_file(csv_local_path, container_name, bronze_blob_name, settings)
    return True, reason


def download_bronze_csv(entry: dict, settings: dict) -> Path:
    from src.azure_storage import download_file

    bronze_blob_name = get_bronze_blob_name(entry)
    container_name = settings["azure"]["bronze_container"]
    local_path = get_work_path(f"bronze/{bronze_blob_name}", settings)
    download_file(container_name, bronze_blob_name, local_path, settings)
    return local_path
