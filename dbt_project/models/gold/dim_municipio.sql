{{ config(materialized='incremental', unique_key='municipio_id') }}

{#
    Dimensao incremental de municipio. Ids nunca sao reatribuidos: a cada execucao,
    so valores novos de municipio recebem id, continuando a numeracao a partir do
    maior id ja existente nesta tabela.
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='municipio',
    id_column='municipio_id'
) }}
