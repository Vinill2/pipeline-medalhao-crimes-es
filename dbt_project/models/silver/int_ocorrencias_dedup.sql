{#
    Etapa 3: remove duplicados pela coluna no_ocorrencia.
    Criterio de desempate: mantem a linha carregada mais recentemente (data_carga maior).
    Isso e uma escolha -- se a regra de negocio for outra (ex: manter a mais antiga),
    e so trocar o "desc" por "asc" abaixo.
#}

{% set unificado = ref('int_ocorrencias_unificado') %}
{% set colunas = get_relation_column_names(unificado, excluded_columns=['linha_numero']) %}

with numeradas as (

    select
        *,
        row_number() over (
            partition by cast(nullif(trim(no_ocorrencia), '') as integer)
            order by data_carga desc
        ) as linha_numero
    from {{ unificado }}
    where nullif(trim(no_ocorrencia), '') is not null

)

{% if colunas %}
select
    {% for coluna in colunas %}
    {{ coluna }}{{ "," if not loop.last }}
    {% endfor %}
from numeradas
where linha_numero = 1
{% else %}
select * from numeradas where linha_numero = 1
{% endif %}
