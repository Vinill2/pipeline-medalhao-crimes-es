{{ config(materialized='incremental', unique_key='tipo_crime_id') }}

{#
    Dimensao incremental de tipo_crime: a categoria da ocorrencia, vinda da
    chave "titulo" em config/sources.json (ex: "ROUBO DE CELULAR"), ligada
    via nome_tabela -> ref_fonte -> titulo dentro de slv_ocorrencias.
    Mesmo padrao incremental das outras dimensoes: ids nunca sao reatribuidos.
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='tipo_crime',
    id_column='tipo_crime_id'
) }}
