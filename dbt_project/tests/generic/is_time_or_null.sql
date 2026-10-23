{#
    Falha se a coluna tiver algum valor que NAO seja uma hora valida no formato
    HH:MM:SS (00:00:00 a 23:59:59). NULL e texto vazio sao aceitos; qualquer
    outro texto nao e.
#}
{% test is_time_or_null(model, column_name) %}

select {{ column_name }} as invalid_value
from {{ model }}
where nullif(trim(cast({{ column_name }} as varchar)), '') is not null
  and not regexp_matches(
      trim(cast({{ column_name }} as varchar)),
      '^([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$'
  )

{% endtest %}
