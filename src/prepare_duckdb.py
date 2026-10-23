import logging

import duckdb

from src.azure_storage import get_work_path, list_blob_names, try_download_file
from src.settings import get_project_path, get_settings

LOGGER = logging.getLogger(__name__)


def configure_logging(settings: dict) -> None:
    logging_settings = settings["logging"]
    logging.basicConfig(level=logging_settings["level"], format=logging_settings["format"])


def download_silver_staging_files(settings: dict) -> list:
    container_name = settings["azure"]["silver_container"]
    prefix = settings["azure"]["silver_staging_prefix"]
    blob_names = list_blob_names(container_name, prefix, settings)
    blob_names = [name for name in blob_names if name.endswith(".parquet")]
    local_paths = []
    for blob_name in blob_names:
        local_path = get_work_path(f"warehouse_input/{blob_name}", settings)
        try_download_file(container_name, blob_name, local_path, settings)
        local_paths.append(local_path)
    return local_paths


def download_reference_table(settings: dict):
    container_name = settings["azure"]["silver_container"]
    blob_name = settings["azure"]["reference_blob_name"]
    local_path = get_work_path(f"warehouse_input/{blob_name}", settings)
    was_downloaded = try_download_file(container_name, blob_name, local_path, settings)
    return local_path if was_downloaded else None


def download_existing_gold_tables(settings: dict) -> dict:
    container_name = settings["azure"]["gold_container"]
    table_names = settings["gold"]["dimension_tables"] + [settings["gold"]["fact_table"]]
    downloaded_tables = {}
    for table_name in table_names:
        blob_name = f"{table_name}.parquet"
        local_path = get_work_path(f"warehouse_input_gold/{blob_name}", settings)
        was_downloaded = try_download_file(container_name, blob_name, local_path, settings)
        if was_downloaded:
            downloaded_tables[table_name] = local_path
    return downloaded_tables


def load_parquet_as_table(connection: duckdb.DuckDBPyConnection, table_name: str, local_path) -> None:
    connection.execute(
        f'create or replace table "{table_name}" as select * from read_parquet(?)', [str(local_path)]
    )


def build_local_warehouse(settings: dict) -> None:
    warehouse_path = get_project_path(settings["paths"]["warehouse_file"])
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    if warehouse_path.exists():
        # o estado que importa vive no Blob, nao no arquivo local -- sempre comeca do zero
        # pra nao acumular lixo de execucoes antigas (GitHub Actions roda em maquina nova
        # a cada vez, mas no VSCode local isso evita resto de execucao anterior tambem).
        warehouse_path.unlink()

    connection = duckdb.connect(str(warehouse_path))

    staging_paths = download_silver_staging_files(settings)
    for local_path in staging_paths:
        table_name = local_path.stem
        load_parquet_as_table(connection, table_name, local_path)
        LOGGER.info("fonte carregada no duckdb local: %s", table_name)

    reference_path = download_reference_table(settings)
    if reference_path:
        load_parquet_as_table(connection, "ref_fonte", reference_path)
        LOGGER.info("tabela de referencia carregada: ref_fonte")
    else:
        LOGGER.warning("ref_fonte.parquet nao encontrada no silver -- rode load_silver_staging antes")

    gold_tables = download_existing_gold_tables(settings)
    for table_name, local_path in gold_tables.items():
        load_parquet_as_table(connection, table_name, local_path)
        LOGGER.info("estado anterior da gold restaurado: %s (ids vao continuar de onde pararam)", table_name)

    connection.close()


def run_prepare() -> None:
    settings = get_settings()
    configure_logging(settings)
    build_local_warehouse(settings)


if __name__ == "__main__":
    run_prepare()
