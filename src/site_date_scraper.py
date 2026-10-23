from datetime import datetime

import requests
from bs4 import BeautifulSoup


def fetch_page_html(page_url: str, settings: dict) -> str:
    download_settings = settings["download"]
    response = requests.get(
        page_url,
        headers={"User-Agent": download_settings["user_agent"]},
        timeout=download_settings["timeout_seconds"],
    )
    response.raise_for_status()
    return response.text


def extract_last_update_text(page_html: str) -> str:
    soup = BeautifulSoup(page_html, "html.parser")

    label_cell = soup.find("th", string="Última Atualização")
    if not label_cell:
        return None

    row = label_cell.find_parent("tr")
    value_cell = row.find("td") if row else None
    if not value_cell:
        return None

    date_span = value_cell.find("span", class_="automatic-local-datetime")
    if not date_span:
        return None

    date_text = date_span.get("data-datetime")
    return date_text


def parse_site_date_text(date_text: str) -> datetime:
    # O site devolve a data com fuso horario (ex: "2026-05-26T14:30:00-03:00").
    # O resto do manifesto (data_atualizacao_sistema) e salvo sem fuso, com
    # datetime.now().isoformat(). Pra poder comparar as duas sem erro de tipo
    # (datetime "aware" vs "naive" nao pode ser comparado direto em Python),
    # tiramos o fuso aqui e tratamos o horario como hora local mesmo.
    parsed_with_timezone = datetime.strptime(date_text, "%Y-%m-%dT%H:%M:%S%z")
    parsed_naive = parsed_with_timezone.replace(tzinfo=None)
    return parsed_naive


def fetch_site_last_update(page_url: str, settings: dict) -> datetime:
    page_html = fetch_page_html(page_url, settings)
    date_text = extract_last_update_text(page_html)
    if not date_text:
        return None
    return parse_site_date_text(date_text)
