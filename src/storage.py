import sqlite3

import pandas as pd

from src.settings import get_project_path


def connect_database(settings: dict) -> sqlite3.Connection:
    database_path = get_project_path(settings["paths"]["database"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    return connection


def get_staging_table_name(entry: dict, settings: dict) -> str:
    staging_table_name = settings["silver"]["table_prefix"] + entry["nome_tabela"]
    return staging_table_name


def send_data(connection: sqlite3.Connection, dataframe: pd.DataFrame, table_name: str, settings: dict) -> int:
    dataframe.to_sql(
        table_name,
        connection,
        if_exists="replace",
        index=False,
        chunksize=settings["silver"]["load_chunk_size"],
    )
    loaded_row_count = len(dataframe)
    return loaded_row_count
