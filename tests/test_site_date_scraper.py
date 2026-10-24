from datetime import datetime

from src.site_date_scraper import extract_last_update_text, parse_site_date_text

PAGE_WITH_DATE = """
<table>
  <tr><th>Fonte</th><td>SESP</td></tr>
  <tr><th>Última Atualização</th>
      <td><span class="automatic-local-datetime" data-datetime="2026-05-26T14:30:00-03:00">26 de maio</span></td></tr>
</table>
"""


def test_extracts_date_text_from_dataset_page():
    assert extract_last_update_text(PAGE_WITH_DATE) == "2026-05-26T14:30:00-03:00"


def test_returns_none_when_label_is_missing():
    assert extract_last_update_text("<table><tr><th>Fonte</th><td>SESP</td></tr></table>") is None


def test_returns_none_when_date_span_is_missing():
    page = "<table><tr><th>Última Atualização</th><td>sem data</td></tr></table>"
    assert extract_last_update_text(page) is None


def test_parse_drops_timezone_but_keeps_local_clock_time():
    parsed = parse_site_date_text("2026-05-26T14:30:00-03:00")
    assert parsed == datetime(2026, 5, 26, 14, 30, 0)
    assert parsed.tzinfo is None
