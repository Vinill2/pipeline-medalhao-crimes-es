import pandas as pd
import pytest

from src.reader import (
    add_load_metadata,
    clean_dataframe_dimension_columns,
    detect_csv_separator,
    detect_file_encoding,
    read_typed_csv,
    standardize_dataframe_columns,
)


def write_csv(path, text, encoding):
    path.write_bytes(text.encode(encoding))
    return path


def test_detects_utf8_with_bom(tmp_path, settings):
    csv_path = write_csv(tmp_path / "a.csv", "A;B\n1;2\n", "utf-8-sig")
    assert detect_file_encoding(csv_path, settings) == "utf-8-sig"


def test_falls_back_to_cp1252_for_windows_files(tmp_path, settings):
    csv_path = write_csv(tmp_path / "a.csv", "MUNICÍPIO;BAIRRO\nSERRA;CENTRO\n", "cp1252")
    assert detect_file_encoding(csv_path, settings) == "cp1252"


@pytest.mark.parametrize("separator", [";", ",", "\t", "|"])
def test_detects_separator(tmp_path, settings, separator):
    csv_path = write_csv(tmp_path / "a.csv", f"A{separator}B{separator}C\n1{separator}2{separator}3\n", "utf-8")
    assert detect_csv_separator(csv_path, "utf-8", settings) == separator


def test_read_typed_csv_reads_accented_cp1252_file(tmp_path, settings):
    csv_path = write_csv(tmp_path / "a.csv", "Nº OCORRENCIA;MUNICÍPIO\n10;VITÓRIA\n", "cp1252")
    dataframe = read_typed_csv(csv_path, settings)
    assert list(dataframe.columns) == ["Nº OCORRENCIA", "MUNICÍPIO"]
    assert dataframe.loc[0, "MUNICÍPIO"] == "VITÓRIA"


def test_standardize_dataframe_columns_does_not_mutate_input():
    original = pd.DataFrame({"Nº OCORRENCIA": [1], "MUNICÍPIO": ["X"]})
    standardized = standardize_dataframe_columns(original)
    assert list(standardized.columns) == ["no_ocorrencia", "municipio"]
    assert list(original.columns) == ["Nº OCORRENCIA", "MUNICÍPIO"]


def test_clean_dimension_columns_only_touches_dimension_columns(settings):
    dataframe = pd.DataFrame(
        {
            "municipio": ["Vitória", "S/I", None],
            "bairro": ["centro", "INDETERMINADO", ""],
            "descricao_livre": ["Texto Com Acento", "S/I", "x"],   # nao e coluna de dimensao
        }
    )
    cleaned = clean_dataframe_dimension_columns(dataframe, settings)
    # "ausente" pode ser None ou NaN dependendo da versao do pandas; o que importa e ser nulo
    assert cleaned["municipio"].iloc[0] == "VITORIA"
    assert cleaned["municipio"].iloc[1:].isna().all()
    assert cleaned["bairro"].iloc[0] == "CENTRO"
    assert cleaned["bairro"].iloc[1:].isna().all()
    assert cleaned["descricao_livre"].tolist() == ["Texto Com Acento", "S/I", "x"]


def test_add_load_metadata_adds_table_name_and_timestamp(settings):
    dataframe = pd.DataFrame({"no_ocorrencia": [1, 2]})
    with_metadata = add_load_metadata(dataframe, "roubo_celular", settings)
    assert with_metadata["nome_tabela"].tolist() == ["roubo_celular", "roubo_celular"]
    assert with_metadata["data_carga"].nunique() == 1
    assert "data_carga" not in dataframe.columns
