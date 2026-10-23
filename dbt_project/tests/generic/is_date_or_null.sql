{#
    Falha se a coluna tiver algum valor que NAO seja uma data valida.
    NULL e texto vazio sao aceitos; texto que nao vira data (ex: "indeterminado",
    "32/13/2024") nao e.
#}
{% test is_date_or_null(model, column_name) %}

select {{ column_name }} as invalid_value
from {{ model }}
where nullif(trim(cast({{ column_name }} as varchar)), '') is not null
  and try_cast(nullif(trim(cast({{ column_name }} as varchar)), '') as date) is null

{% endtest %}
