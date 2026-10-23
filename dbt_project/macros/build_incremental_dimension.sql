{#
    Gera uma dimensao incremental generica: id numerico sequencial + valor texto.
    Na primeira execucao (tabela nao existe), comeca do 1.
    Nas execucoes seguintes, so adiciona valores novos, continuando a numeracao
    a partir do maior id ja existente em {{ this }} -- nunca reseta os ids antigos.

    extra_columns: colunas adicionais vindas da origem (ex: cod_incidente) que devem
    acompanhar cada valor da dimensao. Como um mesmo valor (ex: a mesma agencia) pode
    aparecer em varias linhas com codigos diferentes, usamos MAX() ignorando NULL para
    escolher um unico valor por grupo -- isso e uma suposicao e deve ser conferida com
    dado real: se o codigo de fato varia por linha e nao e constante por categoria,
    essa nao e a coluna certa para virar atributo de dimensao.
#}
{% macro build_incremental_dimension(source_relation, value_column, id_column, extra_columns=[]) %}

{%- set extra_select = extra_columns | map('trim') | map('string') -%}
{%- set extra_select_grouped = [] -%}
{%- for col in extra_columns -%}
    {%- do extra_select_grouped.append('max(' ~ col ~ ') as ' ~ col) -%}
{%- endfor -%}
{%- set extra_select_prefix = ',\n        ' ~ (extra_select_grouped | join(',\n        ')) if extra_columns else '' -%}
{%- set extra_passthrough_prefix = ',\n        ' ~ (extra_columns | join(',\n        ')) if extra_columns else '' -%}

with valores_distintos as (

    select
        nullif(trim({{ value_column }}), '') as {{ value_column }}{{ extra_select_prefix }}
    from {{ source_relation }}
    where nullif(trim({{ value_column }}), '') is not null
    group by nullif(trim({{ value_column }}), '')

)

{% if is_incremental() %}

, valores_novos as (

    select *
    from valores_distintos
    where {{ value_column }} not in (select {{ value_column }} from {{ this }})

)

, maior_id_atual as (

    select coalesce(max({{ id_column }}), 0) as valor
    from {{ this }}

)

select
    maior_id_atual.valor + row_number() over (order by valores_novos.{{ value_column }}) as {{ id_column }},
    valores_novos.{{ value_column }}{{ extra_passthrough_prefix }}
from valores_novos
cross join maior_id_atual

{% else %}

select
    row_number() over (order by {{ value_column }}) as {{ id_column }},
    {{ value_column }}{{ extra_passthrough_prefix }}
from valores_distintos

{% endif %}

{% endmacro %}
