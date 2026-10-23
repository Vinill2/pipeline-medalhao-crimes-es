{#
    Converte uma coluna de data para o tipo DATE do DuckDB.
    try_strptime nunca gera erro -- formato nao reconhecido vira NULL direto,
    sem precisar de try/except ou CASE WHEN pra capturar excecao (diferenca boa
    em relacao ao date() puro do SQLite, que falhava com erro em formato BR).
    Tenta primeiro ISO (AAAA-MM-DD), depois BR (DD/MM/AAAA).
#}
{% macro to_iso_date(column_name) %}
    coalesce(
        try_strptime(nullif(trim({{ column_name }}), ''), '%Y-%m-%d')::date,
        try_strptime(nullif(trim({{ column_name }}), ''), '%d/%m/%Y')::date
    )
{% endmacro %}
