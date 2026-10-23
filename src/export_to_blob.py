import logging

import duckdb

from src.azure_storage import get_work_path, upload_file
from src.settings import get_project_path, get_settings

LOGGER = logging.getLogger(__name__)


def configure_logging(settings: dict) -> None:
    logging_settings = settings["logging"]
    logging.basicConfig(level=logging_settings["level"], format=logging_settings["format"])


def export_table_to_local_parquet(connection: duckdb.DuckDBPyConnection, table_name: str, local_dir) -> str:
    local_path = local_dir / f"{table_name}.parquet"
    connection.execute(f'copy "{table_name}" to \'{local_path}\' (format parquet)')
    return local_path


def export_silver(connection: duckdb.DuckDBPyConnection, local_dir, settings: dict) -> None:
    local_path = export_table_to_local_parquet(connection, "slv_ocorrencias", local_dir)
    blob_name = settings["azure"]["silver_final_blob_name"]
    container_name = settings["azure"]["silver_container"]
    upload_file(local_path, container_name, blob_name, settings)
    LOGGER.info("silver exportada: %s", blob_name)


def export_gold(connection: duckdb.DuckDBPyConnection, local_dir, settings: dict) -> None:
    container_name = settings["azure"]["gold_container"]
    table_names = settings["gold"]["dimension_tables"] + [settings["gold"]["fact_table"]]
    for table_name in table_names:
        local_path = export_table_to_local_parquet(connection, table_name, local_dir)
        blob_name = f"{table_name}.parquet"
        upload_file(local_path, container_name, blob_name, settings)
        LOGGER.info("gold exportada: %s", blob_name)


def run_export() -> None:
    settings = get_settings()
    configure_logging(settings)
    warehouse_path = get_project_path(settings["paths"]["warehouse_file"])
    connection = duckdb.connect(str(warehouse_path))

    local_dir = get_work_path("export", settings)
    local_dir.mkdir(parents=True, exist_ok=True)

    export_silver(connection, local_dir, settings)
    export_gold(connection, local_dir, settings)

    connection.close()


if __name__ == "__main__":
    run_export()
