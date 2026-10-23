{{ config(materialized='incremental', unique_key='tipo_de_local_id') }}

{#
    Dimensao incremental de tipo_de_local. Ids nunca sao reatribuidos: a cada execucao,
    so valores novos de tipo_de_local recebem id, continuando a numeracao a partir do
    maior id ja existente nesta tabela.
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='tipo_de_local',
    id_column='tipo_de_local_id'
) }}
