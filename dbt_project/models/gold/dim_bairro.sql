{{ config(materialized='incremental', unique_key='bairro_id') }}

{#
    Dimensao incremental de bairro. Ids nunca sao reatribuidos: a cada execucao,
    so valores novos de bairro recebem id, continuando a numeracao a partir do
    maior id ja existente nesta tabela.
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='bairro',
    id_column='bairro_id'
) }}
