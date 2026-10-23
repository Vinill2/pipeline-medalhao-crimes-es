{{ config(materialized='incremental', unique_key='uf_id') }}

{#
    Dimensao incremental de uf. Ids nunca sao reatribuidos: a cada execucao,
    so valores novos de uf recebem id, continuando a numeracao a partir do
    maior id ja existente nesta tabela.
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='uf',
    id_column='uf_id'
) }}
