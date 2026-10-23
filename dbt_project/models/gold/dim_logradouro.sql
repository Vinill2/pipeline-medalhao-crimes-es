{{ config(materialized='incremental', unique_key='logradouro_id') }}

{#
    Dimensao incremental de logradouro. Ids nunca sao reatribuidos: a cada execucao,
    so valores novos de logradouro recebem id, continuando a numeracao a partir do
    maior id ja existente nesta tabela.
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='logradouro',
    id_column='logradouro_id'
) }}
