{#
    Une varias relacoes pela UNIAO dos nomes de coluna (nao pela posicao).
    Colunas ausentes em uma relacao viram NULL nessa relacao.
    Resolve o caso em que um arquivo de origem tem mais ou menos colunas que outro.

    Todas as colunas saem como VARCHAR aqui, mesmo que o pandas (na carga da Silver
    etapa 1) tenha inferido tipos diferentes por arquivo (ex: no_ocorrencia virar
    BIGINT num arquivo e VARCHAR em outro, se algum tiver valor nao-numerico nessa
    coluna). O DuckDB, diferente do SQLite, exige que os dois lados de um UNION
    tenham o MESMO tipo -- juntar tipos diferentes quebraria aqui. A tipagem de
    verdade (inteiro, data, etc.) so acontece depois, em slv_ocorrencias, que e
    onde sempre foi a etapa certa pra isso.
#}
{% macro union_relations_by_name(relations) %}
    {%- set all_column_names = [] -%}
    {%- if execute -%}
        {%- for relation in relations -%}
            {%- set relation_columns = adapter.get_columns_in_relation(relation) -%}
            {%- for column in relation_columns -%}
                {%- if column.name not in all_column_names -%}
                    {%- do all_column_names.append(column.name) -%}
                {%- endif -%}
            {%- endfor -%}
        {%- endfor -%}
    {%- endif -%}
    {%- if all_column_names -%}
        {%- for relation in relations %}
            {%- if execute -%}
                {%- set relation_columns = adapter.get_columns_in_relation(relation) -%}
                {%- set relation_column_names = relation_columns | map(attribute='name') | list -%}
            {%- endif %}
select
            {%- for column_name in all_column_names %}
    {% if column_name in relation_column_names -%}
        cast({{ adapter.quote(column_name) }} as varchar)
    {%- else -%}
        cast(null as varchar)
    {%- endif %} as {{ column_name }}{{ "," if not loop.last }}
            {%- endfor %}
from {{ relation }}
            {{ "union all" if not loop.last }}
        {%- endfor -%}
    {%- else -%}
select 1 as placeholder where 1 = 0
    {%- endif -%}
{% endmacro %}
