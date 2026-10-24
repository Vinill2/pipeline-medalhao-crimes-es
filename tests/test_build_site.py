import pytest

from src.build_site import build_docs

pytestmark = pytest.mark.integration


def test_dbt_docs_site_is_generated_with_descriptions_and_lineage(tmp_path):
    docs_path = build_docs(tmp_path / "site")
    html = docs_path.read_text(encoding="utf-8")

    assert docs_path == tmp_path / "site" / "docs" / "index.html"
    assert len(html) > 100_000                          # site estatico completo, nao um arquivo vazio
    assert "fct_ocorrencias" in html and "slv_ocorrencias" in html
    assert "Tabela fato: uma linha por ocorrencia" in html   # descricao do schema.yml chegou no docs
