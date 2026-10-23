{{ config(materialized='incremental', unique_key='orientacao_sexual_id') }}

{#
    Dimensao incremental de orientacao_sexual. Mesmo padrao das outras 9 dimensoes: ids nunca
    sao reatribuidos, so valores novos recebem id na proxima execucao.
    Sem cod_incidente/cod_grupo_incidente aqui -- essas duas colunas ainda nao
    foram corrigidas (pendente, conforme combinado).
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='orientacao_sexual',
    id_column='orientacao_sexual_id'
) }}
