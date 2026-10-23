import argparse
import logging
import subprocess
import sys
import time

from src.export_to_blob import run_export
from src.freshness import get_blob_last_modified, is_derived_up_to_date
from src.load_silver_staging import get_entries_to_load, get_staging_blob_name, run_load
from src.manifest import get_manifest_entries
from src.prepare_duckdb import run_prepare
from src.settings import PROJECT_ROOT, get_settings
from src.sync_raw_files import run_sync

LOGGER = logging.getLogger(__name__)

DBT_DIRECTORY = PROJECT_ROOT / "dbt_project"


class PipelineError(Exception):
    pass


def configure_logging(settings: dict) -> None:
    logging_settings = settings["logging"]
    logging.basicConfig(level=logging_settings["level"], format=logging_settings["format"])


def run_dbt_command(dbt_arguments: list) -> None:
    # roda dentro de dbt_project porque o profiles.yml usa caminhos relativos a essa pasta
    command = [sys.executable, "-m", "dbt.cli.main", *dbt_arguments, "--profiles-dir", "."]
    completed_process = subprocess.run(command, cwd=DBT_DIRECTORY)
    if completed_process.returncode != 0:
        raise PipelineError(f"dbt {dbt_arguments[0]} falhou (codigo {completed_process.returncode})")


def is_gold_up_to_date(entries: list, settings: dict) -> bool:
    """A gold/silver final estao em dia se foram exportadas depois do stg mais recente."""
    azure_settings = settings["azure"]
    silver_container = azure_settings["silver_container"]

    staging_dates = [
        get_blob_last_modified(silver_container, get_staging_blob_name(entry, settings), settings)
        for entry in entries
    ]
    if any(staging_date is None for staging_date in staging_dates):
        return False
    newest_staging_date = max(staging_dates)

    fact_blob_name = f"{settings['gold']['fact_table']}.parquet"
    exported_dates = [
        get_blob_last_modified(azure_settings["gold_container"], fact_blob_name, settings),
        get_blob_last_modified(silver_container, azure_settings["silver_final_blob_name"], settings),
    ]
    if any(exported_date is None for exported_date in exported_dates):
        return False
    return is_derived_up_to_date(newest_staging_date, min(exported_dates))


def run_step(step_label: str, step_function, step_durations: dict):
    LOGGER.info("=== %s ===", step_label)
    started_at = time.monotonic()
    result = step_function()
    step_durations[step_label] = time.monotonic() - started_at
    return result


def log_duration_summary(step_durations: dict, total_started_at: float) -> None:
    LOGGER.info("--- tempo por etapa ---")
    for step_label, duration in step_durations.items():
        LOGGER.info("%-34s %6.1fs", step_label, duration)
    LOGGER.info("%-34s %6.1fs", "TOTAL", time.monotonic() - total_started_at)


def run_pipeline(force: bool = False, skip_tests: bool = False) -> bool:
    """Roda tudo em sequencia. Devolve False se parou cedo por nao haver nada a fazer."""
    settings = get_settings()
    configure_logging(settings)
    total_started_at = time.monotonic()
    step_durations = {}

    run_step("1/6 Bronze: sincronizar", run_sync, step_durations)

    entries = get_manifest_entries(settings)
    entries_to_load = get_entries_to_load(entries, settings, force)
    if not force and not entries_to_load and is_gold_up_to_date(entries, settings):
        LOGGER.info("Nada a fazer: bronze sem novidades e silver/gold ja em dia. Use --force para reprocessar tudo.")
        log_duration_summary(step_durations, total_started_at)
        return False
    LOGGER.info("Datasets a reprocessar no silver: %s", [entry["nome_tabela"] for entry in entries_to_load] or "nenhum (so refaz silver final/gold)")

    load_summary = run_step("2/6 Silver: carregar stg", lambda: run_load(force=force, entries_to_load=entries_to_load), step_durations)
    if load_summary["failed"]:
        raise PipelineError(f"carga do silver falhou em: {sorted(load_summary['failed'])}. Parando antes do dbt para nao gerar a gold com dado incompleto.")

    run_step("3/6 Preparar DuckDB", run_prepare, step_durations)
    run_step("4/6 dbt run", lambda: run_dbt_command(["run"]), step_durations)
    if skip_tests:
        LOGGER.warning("5/6 dbt test PULADO (--skip-tests)")
    else:
        run_step("5/6 dbt test", lambda: run_dbt_command(["test"]), step_durations)
    run_step("6/6 Exportar silver/gold", run_export, step_durations)

    log_duration_summary(step_durations, total_started_at)
    return True


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Roda o pipeline completo: bronze -> silver -> gold.")
    parser.add_argument("--force", action="store_true", help="reprocessa tudo, mesmo se nada mudou (use depois de mudar regras de limpeza)")
    parser.add_argument("--skip-tests", action="store_true", help="nao roda o dbt test (por padrao, falha de teste impede a exportacao)")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    try:
        run_pipeline(force=arguments.force, skip_tests=arguments.skip_tests)
    except PipelineError as error:
        LOGGER.error("Pipeline interrompido: %s", error)
        sys.exit(1)
