import logging
import time

from src.downloader import sync_raw_file_to_bronze
from src.manifest import get_manifest_entries, mark_entry_as_synced, save_manifest_entries
from src.settings import get_settings
from src.site_date_scraper import fetch_site_last_update

LOGGER = logging.getLogger(__name__)


def configure_logging(settings: dict) -> None:
    logging_settings = settings["logging"]
    logging.basicConfig(level=logging_settings["level"], format=logging_settings["format"])


def fetch_current_site_date(entry: dict, settings: dict):
    """Data de 'Ultima Atualizacao' que esta na pagina do dataset AGORA, ou None se nao der pra obter."""
    page_url = entry.get("pagina_dataset")
    if not page_url:
        LOGGER.warning("%s: pagina_dataset nao preenchida no manifesto", entry["nome_tabela"])
        return None

    try:
        scraped_date = fetch_site_last_update(page_url, settings)
    except Exception as error:
        LOGGER.warning("%s: falha ao raspar a data do site (%s)", entry["nome_tabela"], error)
        return None

    if scraped_date is None:
        LOGGER.warning("%s: campo de data nao encontrado na pagina", entry["nome_tabela"])
    return scraped_date


def sync_all_entries(entries: list, settings: dict) -> list:
    updated_entries = []
    uploaded_count = 0
    skipped_count = 0
    for position, entry in enumerate(entries, start=1):
        table_name = entry["nome_tabela"]
        started_at = time.monotonic()
        site_date = fetch_current_site_date(entry, settings)
        was_uploaded, reason = sync_raw_file_to_bronze(entry, site_date, settings)
        elapsed_seconds = time.monotonic() - started_at

        if was_uploaded:
            updated_entries.append(mark_entry_as_synced(entry, site_date))
            uploaded_count += 1
            # salva a cada dataset concluido: se um dos proximos falhar (timeout, etc.),
            # o que ja subiu pro Azure nao e baixado de novo na proxima execucao.
            save_manifest_entries(updated_entries + entries[position:], settings)
            LOGGER.info("[%d/%d] %s: BAIXADO e enviado pro bronze -- %s (%.1fs)", position, len(entries), table_name, reason, elapsed_seconds)
        else:
            updated_entries.append(entry)
            skipped_count += 1
            LOGGER.info("[%d/%d] %s: pulado -- %s (%.1fs)", position, len(entries), table_name, reason, elapsed_seconds)

    LOGGER.info("sync concluido: %d baixado(s), %d pulado(s), %d total", uploaded_count, skipped_count, len(entries))
    return updated_entries


def run_sync() -> list:
    settings = get_settings()
    configure_logging(settings)
    entries = get_manifest_entries(settings)
    updated_entries = sync_all_entries(entries, settings)
    save_manifest_entries(updated_entries, settings)
    return updated_entries


if __name__ == "__main__":
    run_sync()
