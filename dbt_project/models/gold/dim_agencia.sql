{{ config(materialized='incremental', unique_key='agencia_id') }}

{#
    Dimensao incremental de agencia. Ids nunca sao reatribuidos: a cada execucao,
    so valores novos de agencia recebem id, continuando a numeracao a partir do
    maior id ja existente nesta tabela.
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='agencia',
    id_column='agencia_id'
) }}
