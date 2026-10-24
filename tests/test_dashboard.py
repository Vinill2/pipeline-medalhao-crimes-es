import json
import re

import duckdb
import pytest

from src.dashboard import build_dashboard_html, read_gold_aggregates, run_dashboard
from src.synthetic_warehouse import DATASET_NAMES, ROWS_PER_DATASET

pytestmark = pytest.mark.integration

TOTAL = len(DATASET_NAMES) * ROWS_PER_DATASET


@pytest.fixture(scope="module")
def gold_directory(built_warehouse, tmp_path_factory):
    """Exporta a gold do warehouse ficticio para Parquet, como o export_to_blob faz."""
    directory = tmp_path_factory.mktemp("gold")
    connection = duckdb.connect(str(built_warehouse), read_only=True)
    for table in ("fct_ocorrencias", "dim_municipio", "dim_tipo_crime", "dim_sexo"):
        connection.execute(f"copy {table} to '{(directory / (table + '.parquet')).as_posix()}' (format parquet)")
    connection.close()
    return directory


@pytest.fixture(scope="module")
def aggregates(gold_directory):
    return read_gold_aggregates(gold_directory)


def test_kpis_match_the_synthetic_data(aggregates):
    kpis = aggregates["kpis"]
    assert kpis["total"] == TOTAL
    assert kpis["municipalities"] == ROWS_PER_DATASET
    assert kpis["crime_types"] == len(DATASET_NAMES)
    assert kpis["first_date"] == kpis["last_date"] == "2026-03-15"


def test_every_chart_series_adds_up_to_the_total(aggregates):
    for series_name in ("by_month", "by_crime_type", "by_municipality", "by_sex", "by_hour", "by_weekday", "by_age"):
        series = aggregates[series_name]
        assert len(series["labels"]) == len(series["values"]), series_name
        assert sum(series["values"]) == TOTAL, series_name


def test_hour_and_age_buckets_land_where_expected(aggregates):
    by_hour = dict(zip(aggregates["by_hour"]["labels"], aggregates["by_hour"]["values"]))
    assert by_hour["10h"] == TOTAL and by_hour["11h"] == 0
    by_age = dict(zip(aggregates["by_age"]["labels"], aggregates["by_age"]["values"]))
    assert by_age["25-34"] == TOTAL        # idade ficticia = 30
    assert by_age["60+"] == 0


def test_html_embeds_valid_json_and_is_self_contained(aggregates):
    html = build_dashboard_html(aggregates)
    embedded = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert json.loads(embedded)["kpis"]["total"] == TOTAL
    assert "http://" not in html and "https://" not in html.replace("dbt", "")  # sem CDN nem chamada externa


def test_malicious_names_cannot_break_out_of_the_data_script(aggregates):
    hostile = dict(aggregates)
    hostile["by_municipality"] = {"labels": ["</script><script>alert(1)</script>"], "values": [1]}
    html = build_dashboard_html(hostile)
    assert html.count("<script") == 2                        # so os dois scripts legitimos
    embedded = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert json.loads(embedded)["by_municipality"]["labels"][0] == "</script><script>alert(1)</script>"


def test_run_dashboard_writes_the_html_file(gold_directory, tmp_path):
    output = run_dashboard(tmp_path / "site" / "index.html", gold_directory)
    assert output.exists() and "Criminalidade" in output.read_text(encoding="utf-8")


def test_dashboard_publishes_no_row_level_fields(aggregates):
    serialized = json.dumps(aggregates)
    for private_field in ("no_ocorrencia", "logradouro", "bairro"):
        assert private_field not in serialized
