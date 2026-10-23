{{ config(materialized='incremental', unique_key='unidade_origem_pc_id') }}

{#
    Dimensao incremental de unidade_origem_pc. Ids nunca sao reatribuidos: a cada execucao,
    so valores novos de unidade_origem_pc recebem id, continuando a numeracao a partir do
    maior id ja existente nesta tabela.
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='unidade_origem_pc',
    id_column='unidade_origem_pc_id'
) }}
