{{ config(materialized='incremental', unique_key='tipo_objeto_id') }}

{#
    Dimensao incremental de tipo_objeto. Mesmo padrao das outras 9 dimensoes: ids nunca
    sao reatribuidos, so valores novos recebem id na proxima execucao.
    Sem cod_incidente/cod_grupo_incidente aqui -- essas duas colunas ainda nao
    foram corrigidas (pendente, conforme combinado).
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='tipo_objeto',
    id_column='tipo_objeto_id'
) }}
