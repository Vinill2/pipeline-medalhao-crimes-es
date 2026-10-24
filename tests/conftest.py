import pytest

from src.settings import get_settings


@pytest.fixture
def settings() -> dict:
    """Usa o config/settings.json real: assim os testes tambem validam que as chaves existem."""
    return get_settings()


@pytest.fixture(scope="session")
def built_warehouse(tmp_path_factory):
    """Warehouse ficticio ja processado por `dbt run` (compartilhado por toda a suite)."""
    from src.pipeline import run_dbt_command
    from src.synthetic_warehouse import build_synthetic_warehouse

    database_path = tmp_path_factory.mktemp("dbt_clean") / "warehouse.duckdb"
    build_synthetic_warehouse(database_path)
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("DUCKDB_PATH", str(database_path))
        run_dbt_command(["run"])
    return database_path
