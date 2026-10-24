"""Monta o site publicado no GitHub Pages:

    site/index.html       dashboard (le agregados da gold no Azure)
    site/docs/index.html  dicionario de dados e linhagem (dbt docs)

    python -m src.build_site                    # tudo
    python -m src.build_site --skip-dashboard   # so o dbt docs (nao precisa de Azure)

O dbt docs e gerado sobre um warehouse FICTICIO: documentacao e linhagem dependem
so da estrutura dos modelos, nao dos dados.
"""
import argparse
import logging
import os
import shutil
import tempfile
from pathlib import Path

from src.dashboard import run_dashboard
from src.pipeline import DBT_DIRECTORY, run_dbt_command
from src.settings import get_settings
from src.synthetic_warehouse import build_synthetic_warehouse

LOGGER = logging.getLogger(__name__)


def build_docs(site_directory: Path) -> Path:
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "warehouse.duckdb"
        build_synthetic_warehouse(database_path)

        previous_value = os.environ.get("DUCKDB_PATH")
        os.environ["DUCKDB_PATH"] = str(database_path)
        try:
            run_dbt_command(["run"])
            run_dbt_command(["docs", "generate", "--static"])
        finally:
            if previous_value is None:
                os.environ.pop("DUCKDB_PATH", None)
            else:
                os.environ["DUCKDB_PATH"] = previous_value

    docs_path = site_directory / "docs" / "index.html"
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(DBT_DIRECTORY / "target" / "static_index.html", docs_path)
    LOGGER.info("dbt docs gerado: %s", docs_path)
    return docs_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera o site (dashboard + dbt docs).")
    parser.add_argument("--site-dir", default="site", help="pasta de saida (padrao: site)")
    parser.add_argument("--skip-dashboard", action="store_true", help="gera so o dbt docs")
    return parser.parse_args()


def run_build_site(site_directory: Path, skip_dashboard: bool = False) -> None:
    settings = get_settings()
    logging.basicConfig(level=settings["logging"]["level"], format=settings["logging"]["format"])
    build_docs(site_directory)
    if not skip_dashboard:
        run_dashboard(site_directory / "index.html")


if __name__ == "__main__":
    arguments = parse_arguments()
    run_build_site(Path(arguments.site_dir), skip_dashboard=arguments.skip_dashboard)
