from datetime import datetime
from pathlib import Path

import pandas as pd

from src.columns import clean_dimension_cell, get_normalized_sentinel_values, get_standardized_columns


def is_decodable(file_bytes: bytes, encoding: str) -> bool:
    try:
        file_bytes.decode(encoding)
        decodable = True
    except UnicodeDecodeError:
        decodable = False
    return decodable


def detect_file_encoding(file_path: Path, settings: dict) -> str:
    file_bytes = file_path.read_bytes()
    candidate_encodings = settings["csv"]["candidate_encodings"]
    detected_encoding = next(encoding for encoding in candidate_encodings if is_decodable(file_bytes, encoding))
    return detected_encoding


def detect_csv_separator(file_path: Path, encoding: str, settings: dict) -> str:
    with open(file_path, "r", encoding=encoding) as csv_file:
        header_line = csv_file.readline()
    candidate_separators = settings["csv"]["candidate_separators"]
    detected_separator = max(candidate_separators, key=header_line.count)
    return detected_separator


def read_typed_csv(file_path: Path, settings: dict) -> pd.DataFrame:
    encoding = detect_file_encoding(file_path, settings)
    separator = detect_csv_separator(file_path, encoding, settings)
    typed_dataframe = pd.read_csv(
        file_path,
        sep=separator,
        encoding=encoding,
        on_bad_lines="warn",
    )
    return typed_dataframe


def standardize_dataframe_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    standardized_dataframe = dataframe.copy()
    standardized_dataframe.columns = get_standardized_columns(dataframe.columns)
    return standardized_dataframe


def clean_dataframe_dimension_columns(dataframe: pd.DataFrame, settings: dict) -> pd.DataFrame:
    silver_settings = settings["silver"]
    sentinel_values = get_normalized_sentinel_values(silver_settings["sentinel_values"])
    cleaned_dataframe = dataframe.copy()
    for column_name in silver_settings["dimension_columns"]:
        if column_name in cleaned_dataframe.columns:
            cleaned_dataframe[column_name] = cleaned_dataframe[column_name].apply(
                lambda value: clean_dimension_cell(value, sentinel_values)
            )
    return cleaned_dataframe


def add_load_metadata(dataframe: pd.DataFrame, table_name: str, settings: dict) -> pd.DataFrame:
    silver_settings = settings["silver"]
    load_timestamp = datetime.now().isoformat(timespec="seconds")
    dataframe_with_metadata = dataframe.assign(
        **{
            silver_settings["load_date_column"]: load_timestamp,
            silver_settings["table_name_column"]: table_name,
        }
    )
    return dataframe_with_metadata
