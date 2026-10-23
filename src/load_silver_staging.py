import argparse
import logging
import time

import pandas as pd

from src.azure_storage import get_work_path, upload_file
from src.downloader import download_bronze_csv, get_bronze_blob_name
from src.freshness import get_blob_last_modified, is_derived_up_to_date
from src.manifest import get_manifest_entries
from src.reader import add_load_metadata, clean_dataframe_dimension_columns, read_typed_csv, standardize_dataframe_columns
from src.settings import get_settings

LOGGER = logging.getLogger(__name__)


def configure_logging(settings: dict) -> None:
    logging_settings = settings["logging"]
    logging.basicConfig(level=logging_settings["level"], format=logging_settings["format"])


def get_staging_blob_name(entry: dict, settings: dict) -> str:
    prefix = settings["azure"]["silver_staging_prefix"]
    staging_blob_name = f"{prefix}/stg_{entry['nome_tabela']}.parquet"
    return staging_blob_name


def load_entry_to_silver(entry: dict, settings: dict) -> int:
    csv_local_path = download_bronze_csv(entry, settings)
    typed_dataframe = read_typed_csv(csv_local_path, settings)
    standardized_dataframe = standardize_dataframe_columns(typed_dataframe)
    cleaned_dataframe = clean_dataframe_dimension_columns(standardized_dataframe, settings)
    staged_dataframe = add_load_metadata(cleaned_dataframe, entry["nome_tabela"], settings)

    local_parquet_path = get_work_path(f"silver_staging/stg_{entry['nome_tabela']}.parquet", settings)
    local_parquet_path.parent.mkdir(parents=True, exist_ok=True)
    staged_dataframe.to_parquet(local_parquet_path, index=False)

    staging_blob_name = get_staging_blob_name(entry, settings)
    container_name = settings["azure"]["silver_container"]
    upload_file(local_parquet_path, container_name, staging_blob_name, settings)

    loaded_row_count = len(staged_dataframe)
    return loaded_row_count


def is_staging_up_to_date(entry: dict, settings: dict) -> bool:
    bronze_last_modified = get_blob_last_modified(settings["azure"]["bronze_container"], get_bronze_blob_name(entry), settings)
    staging_last_modified = get_blob_last_modified(settings["azure"]["silver_container"], get_staging_blob_name(entry, settings), settings)
    return is_derived_up_to_date(bronze_last_modified, staging_last_modified)


def get_entries_to_load(entries: list, settings: dict, force: bool = False) -> list:
    """Datasets cujo stg precisa ser (re)gerado: stg ausente ou mais antigo que o CSV do bronze."""
    if force:
        return list(entries)
    return [entry for entry in entries if not is_staging_up_to_date(entry, settings)]


def load_all_entries(entries: list, settings: dict, entries_to_load: list = None, force: bool = False) -> dict:
    if entries_to_load is None:
        entries_to_load = get_entries_to_load(entries, settings, force)
    names_to_load = {entry["nome_tabela"] for entry in entries_to_load}

    load_summary = {"loaded": {}, "failed": {}, "skipped": []}
    for position, entry in enumerate(entries, start=1):
        table_name = entry["nome_tabela"]
        if table_name not in names_to_load:
            load_summary["skipped"].append(table_name)
            LOGGER.info("[%d/%d] %s: pulado -- stg ja esta mais novo que o bronze", position, len(entries), table_name)
            continue

        started_at = time.monotonic()
        try:
            load_summary["loaded"][table_name] = load_entry_to_silver(entry, settings)
            LOGGER.info("[%d/%d] %s: carregado no silver, %s linhas (%.1fs)", position, len(entries), table_name, load_summary["loaded"][table_name], time.monotonic() - started_at)
        except Exception as error:
            load_summary["failed"][table_name] = str(error)
            LOGGER.error("[%d/%d] %s: FALHOU -- %s", position, len(entries), table_name, error)

    LOGGER.info(
        "carga silver concluida: %d carregado(s), %d pulado(s), %d falha(s)",
        len(load_summary["loaded"]), len(load_summary["skipped"]), len(load_summary["failed"]),
    )
    return load_summary


def build_reference_dataframe(entries: list) -> pd.DataFrame:
    reference_rows = [
        {"nome_tabela": entry["nome_tabela"], "titulo": entry["titulo"]} for entry in entries
    ]
    reference_dataframe = pd.DataFrame(reference_rows)
    return reference_dataframe


def upload_reference_table(entries: list, settings: dict) -> None:
    reference_dataframe = build_reference_dataframe(entries)
    local_parquet_path = get_work_path("silver_staging/ref_fonte.parquet", settings)
    local_parquet_path.parent.mkdir(parents=True, exist_ok=True)
    reference_dataframe.to_parquet(local_parquet_path, index=False)

    reference_blob_name = settings["azure"]["reference_blob_name"]
    container_name = settings["azure"]["silver_container"]
    upload_file(local_parquet_path, container_name, reference_blob_name, settings)


def run_load(force: bool = False, entries_to_load: list = None) -> dict:
    settings = get_settings()
    configure_logging(settings)
    entries = get_manifest_entries(settings)
    load_summary = load_all_entries(entries, settings, entries_to_load=entries_to_load, force=force)
    upload_reference_table(entries, settings)
    return load_summary


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carrega os CSVs do bronze como Parquet (stg) no silver.")
    parser.add_argument("--force", action="store_true", help="reprocessa todos os datasets, mesmo os que ja estao em dia")
    return parser.parse_args()


if __name__ == "__main__":
    run_load(force=parse_arguments().force)
