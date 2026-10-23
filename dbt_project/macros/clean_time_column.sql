{#
    Mantem apenas valores no formato HH:MM:SS. Qualquer outro valor -- incluindo
    "indeterminado" em qualquer variacao -- vira NULL. DuckDB suporta GLOB igual
    ao SQLite, entao a logica nao muda.
#}
{% macro clean_time_column(column_name) %}
    case
        when {{ column_name }} glob '[0-9][0-9]:[0-9][0-9]:[0-9][0-9]' then {{ column_name }}
        else null
    end
{% endmacro %}
