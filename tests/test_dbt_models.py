"""Testes de integracao: rodam o dbt DE VERDADE (via o mesmo caminho do pipeline) sobre dados ficticios."""
import shutil

import duckdb
import pytest

from src.pipeline import PipelineError, run_dbt_command
from src.synthetic_warehouse import DATASET_NAMES, ROWS_PER_DATASET, build_row, build_synthetic_warehouse, insert_stg_row

pytestmark = pytest.mark.integration


def use_warehouse(monkeypatch, database_path):
    monkeypatch.setenv("DUCKDB_PATH", str(database_path))


def fetch_one(database_path, sql):
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        return connection.execute(sql).fetchone()[0]
    finally:
        connection.close()


def test_all_expected_tables_are_built(built_warehouse, settings):
    connection = duckdb.connect(str(built_warehouse), read_only=True)
    tables = {row[0] for row in connection.execute("show tables").fetchall()}
    connection.close()
    expected = set(settings["gold"]["dimension_tables"]) | {settings["gold"]["fact_table"], "slv_ocorrencias"}
    assert expected <= tables, f"faltando: {sorted(expected - tables)}"


def test_every_synthetic_occurrence_reaches_the_fact_table(built_warehouse, settings):
    total = fetch_one(built_warehouse, f"select count(*) from {settings['gold']['fact_table']}")
    assert total == len(DATASET_NAMES) * ROWS_PER_DATASET


def test_fact_table_has_no_orphan_dimension_ids(built_warehouse):
    orphans = fetch_one(
        built_warehouse,
        "select count(*) from fct_ocorrencias f left join dim_municipio d using (municipio_id) "
        "where f.municipio_id is not null and d.municipio is null",
    )
    assert orphans == 0


def test_quality_tests_pass_on_clean_data(built_warehouse, monkeypatch):
    use_warehouse(monkeypatch, built_warehouse)
    run_dbt_command(["test"])      # levanta PipelineError se qualquer teste falhar


@pytest.mark.parametrize(
    "description, corrupting_sql",
    [
        ("hora com texto", "update slv_ocorrencias set hora_do_fato = 'lixo' where no_ocorrencia = 1"),
        ("hora fora do intervalo", "update slv_ocorrencias set hora_de_criacao = '25:99:00' where no_ocorrencia = 1"),
        ("no_ocorrencia duplicado", "insert into slv_ocorrencias select * from slv_ocorrencias where no_ocorrencia = 1"),
        ("no_ocorrencia nulo", "update slv_ocorrencias set no_ocorrencia = null where no_ocorrencia = 1"),
    ],
)
def test_quality_tests_catch_bad_data(built_warehouse, tmp_path, monkeypatch, description, corrupting_sql):
    corrupted_copy = tmp_path / "corrompido.duckdb"
    shutil.copy(built_warehouse, corrupted_copy)
    connection = duckdb.connect(str(corrupted_copy))
    connection.execute(corrupting_sql)
    connection.close()

    use_warehouse(monkeypatch, corrupted_copy)
    with pytest.raises(PipelineError):
        run_dbt_command(["test"])


def test_dimension_ids_are_stable_and_new_values_get_next_id(tmp_path, monkeypatch):
    """A promessa central do projeto: reprocessar nunca reatribui id de dimensao."""
    database_path = tmp_path / "warehouse.duckdb"
    build_synthetic_warehouse(database_path)
    use_warehouse(monkeypatch, database_path)
    run_dbt_command(["run"])

    connection = duckdb.connect(str(database_path), read_only=True)
    ids_before = dict(connection.execute("select municipio, municipio_id from dim_municipio").fetchall())
    connection.close()
    assert len(ids_before) == ROWS_PER_DATASET

    # chega uma ocorrencia nova, com um municipio que nunca apareceu. O nome vem ANTES dos
    # outros em ordem alfabetica de proposito: um rebuild completo (nao incremental) empurraria
    # os ids antigos para frente, e este teste pegaria isso.
    connection = duckdb.connect(str(database_path))
    new_row = build_row(99, 0, DATASET_NAMES[0])
    new_row.update(no_ocorrencia="9999", municipio="AAA NOVA CIDADE")
    insert_stg_row(connection, DATASET_NAMES[0], new_row)
    connection.close()
    run_dbt_command(["run"])

    connection = duckdb.connect(str(database_path), read_only=True)
    ids_after = dict(connection.execute("select municipio, municipio_id from dim_municipio").fetchall())
    connection.close()

    for municipality, old_id in ids_before.items():
        assert ids_after[municipality] == old_id, f"id de {municipality} mudou"
    assert ids_after["AAA NOVA CIDADE"] == max(ids_before.values()) + 1
