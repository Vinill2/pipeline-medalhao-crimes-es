"""Monta um warehouse DuckDB pequeno e ficticio (18 tabelas stg_* + ref_fonte).

Serve para rodar o dbt de verdade nos testes, no CI e na geracao do dbt docs, sem Azure
e sem dados reais. So a ESTRUTURA importa, os valores sao inventados.
"""
from pathlib import Path

import duckdb

DATASET_NAMES = [
    "homicidio_feminicidio", "violencia_domestica", "crime_informatico", "estelionato_fraude",
    "roubo_celular", "roubo_bicicleta", "roubo_veiculo", "furto_celular", "furto_bicicleta",
    "furto_veiculo", "roubo_transporte_coletivo", "roubo_residencia", "roubo_comercio",
    "roubo_pessoa", "furto_residencia", "furto_transporte_coletivo", "furto_comercio", "furto_pessoa",
]
ROWS_PER_DATASET = 3

DIMENSION_SOURCE_COLUMNS = [
    "tipo_de_boletim", "agencia", "unidade", "unidade_origem_pc", "uf", "municipio", "bairro",
    "logradouro", "meios", "orientacao_sexual", "tipo_objeto", "acao_objeto", "tipo", "marca",
    "modelo", "cor_veiculo", "utilidade_do_veiculo", "tipo_de_incidente", "grupo_de_incidente",
]
ALL_COLUMNS = [
    "no_ocorrencia", "data_carga", "nome_tabela", "hora_do_fato", "hora_de_criacao", "data_do_fato",
    "data_de_criacao", "idade", "cor", "sexo", "tipo_de_local", "cod_incidente", "cod_grupo_incidente",
    "hora", "data", "cutis", "genero", "tipo_local",
] + DIMENSION_SOURCE_COLUMNS


def build_row(dataset_index: int, row_index: int, dataset_name: str) -> dict:
    row = {column: f"{column}_{row_index}" for column in DIMENSION_SOURCE_COLUMNS}
    row.update(
        no_ocorrencia=str(dataset_index * 10 + row_index + 1),
        data_carga="2026-01-01T00:00:00",
        nome_tabela=dataset_name,
        hora_do_fato="10:30:00",
        hora_de_criacao="11:00:00",
        data_do_fato="2026-03-15",
        data_de_criacao="16/03/2026",     # formato BR de proposito: a macro to_iso_date precisa converter
        idade="30",
        cor="BRANCA",
        sexo="M",
        tipo_de_local="RUA",
        cod_incidente="1",
        cod_grupo_incidente="1",
        # colunas sinonimas ausentes chegam NULL (o reader.py converte vazio em None), nao ""
        hora=None, data=None, cutis=None, genero=None, tipo_local=None,
    )
    return row


def sql_literal(value) -> str:
    return "cast(null as varchar)" if value is None else f"'{value}'"


def insert_stg_row(connection, dataset_name: str, row: dict) -> None:
    values = ", ".join(sql_literal(row[column]) for column in ALL_COLUMNS)
    connection.execute(f"insert into stg_{dataset_name} values ({values})")


def build_synthetic_warehouse(database_path) -> None:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path))
    references = ",".join(f"('{name}', 'Titulo {name}')" for name in DATASET_NAMES)
    connection.execute(f"create table ref_fonte as select * from (values {references}) t(nome_tabela, titulo)")
    for dataset_index, dataset_name in enumerate(DATASET_NAMES):
        rows = [build_row(dataset_index, row_index, dataset_name) for row_index in range(ROWS_PER_DATASET)]
        select_statements = " union all ".join(
            "select " + ", ".join(f"{sql_literal(row[column])} as {column}" for column in ALL_COLUMNS) for row in rows
        )
        connection.execute(f"create table stg_{dataset_name} as {select_statements}")
    connection.close()
