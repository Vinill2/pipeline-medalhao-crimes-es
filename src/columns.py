import re
import unicodedata

import pandas as pd


def strip_accents(text: str) -> str:
    normalized_text = unicodedata.normalize("NFKD", text)
    text_without_accents = "".join(
        character for character in normalized_text if not unicodedata.combining(character)
    )
    return text_without_accents


def normalize_column_name(column_name: str) -> str:
    lowercase_name = str(column_name).strip().lower()
    name_without_accents = strip_accents(lowercase_name)
    snake_case_name = re.sub(r"[^a-z0-9]+", "_", name_without_accents).strip("_")
    return snake_case_name


def get_standardized_columns(column_names: list) -> list:
    standardized_columns = [normalize_column_name(name) for name in column_names]
    return standardized_columns


def clean_dimension_cell(value, sentinel_values: set):
    is_missing_value = value is None or pd.isna(value)
    if is_missing_value:
        return None
    text_value = str(value).strip()
    if text_value == "":
        return None
    text_without_accents = strip_accents(text_value)
    cleaned_value = text_without_accents.upper()
    is_sentinel_value = cleaned_value in sentinel_values
    return None if is_sentinel_value else cleaned_value


def get_normalized_sentinel_values(sentinel_values: list) -> set:
    normalized_sentinel_values = {
        strip_accents(value).strip().upper() for value in sentinel_values
    }
    return normalized_sentinel_values
