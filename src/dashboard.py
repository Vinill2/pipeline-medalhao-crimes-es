"""Dashboard estatico (um unico .html) gerado a partir da camada gold.

Le so agregados (contagens por mes, municipio, tipo de crime...): nenhum numero de
ocorrencia, logradouro ou dado individual vai para a pagina publicada.

    python -m src.dashboard --output site/index.html                # le a gold do Azure
    python -m src.dashboard --output site/index.html --gold-dir DIR # le Parquets locais
"""
import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from src.azure_storage import download_file
from src.settings import get_project_path, get_settings

LOGGER = logging.getLogger(__name__)

REQUIRED_GOLD_TABLES = ["fct_ocorrencias", "dim_municipio", "dim_tipo_crime", "dim_sexo"]
WEEKDAY_LABELS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"]   # dayofweek() do DuckDB: domingo = 0
AGE_BANDS = [("0-11", 0, 11), ("12-17", 12, 17), ("18-24", 18, 24), ("25-34", 25, 34), ("35-44", 35, 44), ("45-59", 45, 59), ("60+", 60, 200)]


def download_gold_tables(destination_directory: Path, settings: dict) -> Path:
    container_name = settings["azure"]["gold_container"]
    for table_name in REQUIRED_GOLD_TABLES:
        download_file(container_name, f"{table_name}.parquet", destination_directory / f"{table_name}.parquet", settings)
        LOGGER.info("gold baixada: %s", table_name)
    return destination_directory


def open_gold_connection(gold_directory: Path):
    connection = duckdb.connect()
    for table_name in REQUIRED_GOLD_TABLES:
        parquet_path = (gold_directory / f"{table_name}.parquet").as_posix().replace("'", "''")
        connection.execute(f"create view {table_name} as select * from read_parquet('{parquet_path}')")
    # uma unica versao "limpa" das colunas usadas nos graficos
    connection.execute(
        """
        create view fatos as
        select municipio_id, tipo_crime_id, sexo_id,
               try_cast(data_do_fato as date) as data_fato,
               try_cast(substr(hora_do_fato, 1, 2) as integer) as hora_fato,
               try_cast(idade as integer) as idade_anos
        from fct_ocorrencias
        """
    )
    return connection


def to_series(rows: list) -> dict:
    return {"labels": [str(row[0]) for row in rows], "values": [int(row[1]) for row in rows]}


def read_gold_aggregates(gold_directory: Path) -> dict:
    connection = open_gold_connection(gold_directory)
    try:
        total, municipalities, first_date, last_date = connection.execute(
            "select count(*), count(distinct municipio_id), min(data_fato), max(data_fato) from fatos"
        ).fetchone()

        by_month = connection.execute(
            "select strftime(data_fato, '%Y-%m'), count(*) from fatos where data_fato is not null group by 1 order by 1"
        ).fetchall()
        by_municipality = connection.execute(
            "select m.municipio, count(*) as total from fatos f join dim_municipio m using (municipio_id) group by 1 order by total desc, 1 limit 15"
        ).fetchall()
        by_crime_type = connection.execute(
            "select t.tipo_crime, count(*) as total from fatos f join dim_tipo_crime t using (tipo_crime_id) group by 1 order by total desc, 1"
        ).fetchall()
        by_sex = connection.execute(
            "select s.sexo, count(*) as total from fatos f join dim_sexo s using (sexo_id) group by 1 order by total desc, 1"
        ).fetchall()
        by_hour = dict(connection.execute("select hora_fato, count(*) from fatos where hora_fato between 0 and 23 group by 1").fetchall())
        by_weekday = dict(connection.execute("select dayofweek(data_fato), count(*) from fatos where data_fato is not null group by 1").fetchall())
        by_age = [
            (label, connection.execute(f"select count(*) from fatos where idade_anos between {low} and {high}").fetchone()[0])
            for label, low, high in AGE_BANDS
        ]
    finally:
        connection.close()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "kpis": {
            "total": int(total),
            "municipalities": int(municipalities),
            "crime_types": len(by_crime_type),
            "first_date": str(first_date) if first_date else None,
            "last_date": str(last_date) if last_date else None,
        },
        "by_month": to_series(by_month),
        "by_municipality": to_series(by_municipality),
        "by_crime_type": to_series(by_crime_type),
        "by_sex": to_series(by_sex),
        "by_hour": {"labels": [f"{hour:02d}h" for hour in range(24)], "values": [int(by_hour.get(hour, 0)) for hour in range(24)]},
        "by_weekday": {"labels": WEEKDAY_LABELS, "values": [int(by_weekday.get(day, 0)) for day in range(7)]},
        "by_age": to_series(by_age),
    }


def serialize_for_html(data: dict) -> str:
    # Dentro de um <script>, "</script>" fecharia a tag antes da hora. Escapar <, > e & como \\uXXXX
    # e o padrao seguro: JSON.parse devolve o texto original, mas o HTML nunca ve um "<".
    serialized = json.dumps(data, ensure_ascii=False)
    return serialized.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def build_dashboard_html(aggregates: dict) -> str:
    return HTML_TEMPLATE.replace("__DATA__", serialize_for_html(aggregates))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera o dashboard estatico a partir da gold.")
    parser.add_argument("--output", required=True, help="caminho do .html a gerar")
    parser.add_argument("--gold-dir", help="pasta com os Parquets da gold (sem isso, baixa do Azure)")
    return parser.parse_args()


def run_dashboard(output_path: Path, gold_directory: Path = None) -> Path:
    settings = get_settings()
    logging.basicConfig(level=settings["logging"]["level"], format=settings["logging"]["format"])
    if gold_directory is None:
        gold_directory = download_gold_tables(get_project_path("data/work/gold_for_dashboard"), settings)
    aggregates = read_gold_aggregates(gold_directory)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_dashboard_html(aggregates), encoding="utf-8")
    LOGGER.info("dashboard gerado: %s (%d ocorrencias)", output_path, aggregates["kpis"]["total"])
    return output_path


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Criminalidade no Espírito Santo</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--text:#1f2328;--muted:#6b7280;--line:#e5e7eb;--accent:#2b6cb0;--accent-soft:#bcd3ec}
@media (prefers-color-scheme: dark){:root{--bg:#14171a;--card:#1d2125;--text:#e6e8ea;--muted:#9aa3ad;--line:#2d333b;--accent:#6fa8e0;--accent-soft:#2c4a68}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.5rem;margin:0 0 4px}
.sub{color:var(--muted);margin:0 0 20px}
.sub a{color:var(--accent)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:16px}
.kpi,.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi b{display:block;font-size:1.6rem}
.kpi span{color:var(--muted);font-size:.85rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:12px}
.wide{grid-column:1/-1}
h2{font-size:1rem;margin:0 0 10px}
.bars{display:grid;gap:6px}
.bar{display:grid;grid-template-columns:minmax(90px,38%) 1fr auto;gap:8px;align-items:center;font-size:.85rem}
.bar i{display:block;height:14px;border-radius:3px;background:var(--accent)}
.bar .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar .num{color:var(--muted);font-variant-numeric:tabular-nums}
svg{width:100%;height:auto;display:block}
svg text{fill:var(--muted);font-size:11px}
.scroll{overflow-x:auto}
footer{color:var(--muted);font-size:.8rem;margin-top:20px}
@media (max-width:520px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<main>
  <h1>Criminalidade no Espírito Santo</h1>
  <p class="sub">Ocorrências registradas, a partir dos dados abertos do governo do ES. <a href="docs/">Dicionário de dados e linhagem (dbt docs)</a></p>
  <div class="kpis" id="kpis"></div>
  <div class="grid">
    <div class="card wide"><h2>Ocorrências por mês</h2><div class="scroll" id="by_month"></div></div>
    <div class="card"><h2>Tipos de crime</h2><div class="bars" id="by_crime_type"></div></div>
    <div class="card"><h2>Top 15 municípios</h2><div class="bars" id="by_municipality"></div></div>
    <div class="card"><h2>Por hora do dia</h2><div id="by_hour"></div></div>
    <div class="card"><h2>Por dia da semana</h2><div id="by_weekday"></div></div>
    <div class="card"><h2>Por faixa etária</h2><div class="bars" id="by_age"></div></div>
    <div class="card"><h2>Por sexo</h2><div class="bars" id="by_sex"></div></div>
  </div>
  <footer id="footer"></footer>
</main>
<script id="dashboard-data" type="application/json">__DATA__</script>
<script>
(function () {
  var data = JSON.parse(document.getElementById("dashboard-data").textContent);
  var nf = new Intl.NumberFormat("pt-BR");
  var MONTHS = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
  function el(id) { return document.getElementById(id); }
  function text(value) { var s = document.createElement("span"); s.textContent = value; return s.innerHTML; }

  function kpi(value, label) { return '<div class="kpi"><b>' + text(value) + '</b><span>' + text(label) + '</span></div>'; }
  var k = data.kpis;
  el("kpis").innerHTML =
    kpi(nf.format(k.total), "ocorrências") +
    kpi(nf.format(k.municipalities), "municípios") +
    kpi(nf.format(k.crime_types), "tipos de crime") +
    kpi(k.first_date ? k.first_date.slice(0, 4) + " – " + k.last_date.slice(0, 4) : "–", "período dos fatos");

  function barList(id, series) {
    var max = Math.max.apply(null, series.values.concat([1]));
    el(id).innerHTML = series.labels.map(function (label, i) {
      var pct = (series.values[i] / max * 100).toFixed(1);
      return '<div class="bar"><span class="name" title="' + text(label) + '">' + text(label) + '</span>' +
             '<i style="width:' + pct + '%"></i><span class="num">' + nf.format(series.values[i]) + '</span></div>';
    }).join("");
  }

  function columnChart(id, series, labelEvery) {
    var w = Math.max(360, series.labels.length * 26), h = 170, pad = 24, max = Math.max.apply(null, series.values.concat([1]));
    var slot = (w - pad) / series.labels.length, parts = [];
    series.values.forEach(function (v, i) {
      var bh = v / max * (h - pad - 8), x = pad + i * slot + slot * 0.15;
      parts.push('<rect x="' + x.toFixed(1) + '" y="' + (h - pad - bh).toFixed(1) + '" width="' + (slot * 0.7).toFixed(1) + '" height="' + bh.toFixed(1) + '" rx="2" fill="var(--accent)"><title>' + text(series.labels[i] + ": " + nf.format(v)) + '</title></rect>');
      if (i % labelEvery === 0) parts.push('<text x="' + (x + slot * 0.35).toFixed(1) + '" y="' + (h - 8) + '" text-anchor="middle">' + text(series.labels[i]) + '</text>');
    });
    el(id).innerHTML = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img">' + parts.join("") + '</svg>';
  }

  function monthLabel(ym) { return MONTHS[parseInt(ym.slice(5, 7), 10) - 1] + "/" + ym.slice(2, 4); }
  function lineChart(id, series) {
    var n = series.labels.length, w = Math.max(640, n * 18), h = 200, pad = 36, max = Math.max.apply(null, series.values.concat([1]));
    if (!n) { el(id).textContent = "Sem dados."; return; }
    var step = n > 1 ? (w - pad - 8) / (n - 1) : 0, pts = series.values.map(function (v, i) {
      return [pad + i * step, h - 26 - v / max * (h - 40)];
    });
    var line = pts.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" ");
    var area = pad + "," + (h - 26) + " " + line + " " + pts[n - 1][0].toFixed(1) + "," + (h - 26);
    var every = Math.ceil(n / 14), parts = [
      '<polygon points="' + area + '" fill="var(--accent-soft)" opacity="0.6"/>',
      '<polyline points="' + line + '" fill="none" stroke="var(--accent)" stroke-width="2"/>',
      '<text x="4" y="14">' + text(nf.format(max)) + '</text>', '<text x="4" y="' + (h - 28) + '">0</text>'
    ];
    series.labels.forEach(function (ym, i) {
      parts.push('<circle cx="' + pts[i][0].toFixed(1) + '" cy="' + pts[i][1].toFixed(1) + '" r="2.5" fill="var(--accent)"><title>' + text(monthLabel(ym) + ": " + nf.format(series.values[i])) + '</title></circle>');
      if (i % every === 0) parts.push('<text x="' + pts[i][0].toFixed(1) + '" y="' + (h - 8) + '" text-anchor="middle">' + text(monthLabel(ym)) + '</text>');
    });
    el(id).innerHTML = '<svg viewBox="0 0 ' + w + ' ' + h + '" style="min-width:' + Math.min(w, 900) + 'px" role="img">' + parts.join("") + '</svg>';
  }

  lineChart("by_month", data.by_month);
  barList("by_crime_type", data.by_crime_type);
  barList("by_municipality", data.by_municipality);
  columnChart("by_hour", data.by_hour, 3);
  columnChart("by_weekday", data.by_weekday, 1);
  barList("by_age", data.by_age);
  barList("by_sex", data.by_sex);
  el("footer").textContent = "Fonte: dados.es.gov.br (SESP/ES). Atualizado em " + data.generated_at.replace("T", " ").slice(0, 16) + " UTC. Somente agregados; nenhum registro individual é publicado.";
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    arguments = parse_arguments()
    run_dashboard(Path(arguments.output), Path(arguments.gold_dir) if arguments.gold_dir else None)
