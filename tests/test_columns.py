import pandas as pd
import pytest

from src.columns import (
    clean_dimension_cell,
    get_normalized_sentinel_values,
    get_standardized_columns,
    normalize_column_name,
    strip_accents,
)


def test_strip_accents_removes_diacritics():
    assert strip_accents("MUNICÍPIO São José") == "MUNICIPIO Sao Jose"


@pytest.mark.parametrize(
    "raw_name, expected",
    [
        ("Nº OCORRENCIA", "no_ocorrencia"),      # º (ordinal) vira "no"
        ("MUNICÍPIO", "municipio"),
        ("TIPO LOCAL", "tipo_local"),
        ("  Data do Fato  ", "data_do_fato"),
        ("Hora/Fato", "hora_fato"),
    ],
)
def test_normalize_column_name(raw_name, expected):
    assert normalize_column_name(raw_name) == expected


def test_degree_sign_is_not_the_same_as_ordinal_indicator():
    # Caso real que ja nos pegou: "N°" (grau) e "Nº" (ordinal) parecem iguais mas
    # normalizam diferente. Este teste documenta o comportamento para nao ser esquecido.
    assert normalize_column_name("N° Ocorrência") == "n_ocorrencia"
    assert normalize_column_name("Nº Ocorrência") == "no_ocorrencia"


def test_get_standardized_columns_keeps_order():
    assert get_standardized_columns(["DATA", "Nº OCORRENCIA"]) == ["data", "no_ocorrencia"]


def test_sentinel_values_are_normalized_without_accents_and_uppercase():
    sentinels = get_normalized_sentinel_values(["S/I", "não informado"])
    assert sentinels == {"S/I", "NAO INFORMADO"}


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        (float("nan"), None),
        (pd.NA, None),
        ("", None),
        ("   ", None),
        ("S/I", None),
        ("Não Informado", None),
        ("Vitória", "VITORIA"),
        ("  serra ", "SERRA"),
        (123, "123"),
    ],
)
def test_clean_dimension_cell(value, expected):
    sentinels = get_normalized_sentinel_values(["S/I", "NÃO INFORMADO"])
    assert clean_dimension_cell(value, sentinels) == expected
