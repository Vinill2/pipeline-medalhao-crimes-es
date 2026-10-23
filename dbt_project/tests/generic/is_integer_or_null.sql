{#
    Falha se a coluna tiver algum valor que nao seja so digitos.
    NULL e texto vazio sao aceitos; texto (ex: "S/I", "30 anos") ou numero
    com sinal/decimal (ex: "-1", "30.5") nao e.
#}
{% test is_integer_or_null(model, column_name) %}

select {{ column_name }} as invalid_value
from {{ model }}
where nullif(trim(cast({{ column_name }} as varchar)), '') is not null
  and not regexp_matches(trim(cast({{ column_name }} as varchar)), '^[0-9]+$')

{% endtest %}
