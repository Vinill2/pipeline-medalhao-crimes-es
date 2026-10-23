{{ config(materialized='incremental', unique_key='unidade_id') }}

{#
    Dimensao incremental de unidade. Ids nunca sao reatribuidos: a cada execucao,
    so valores novos de unidade recebem id, continuando a numeracao a partir do
    maior id ja existente nesta tabela.
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='unidade',
    id_column='unidade_id'
) }}
