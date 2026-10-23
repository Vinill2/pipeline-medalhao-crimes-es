{{ config(materialized='incremental', unique_key='sexo_id') }}

{#
    Dimensao incremental de sexo. Mesmo padrao das outras 9 dimensoes: ids nunca
    sao reatribuidos, so valores novos recebem id na proxima execucao.
    Sem cod_incidente/cod_grupo_incidente aqui -- essas duas colunas ainda nao
    foram corrigidas (pendente, conforme combinado).
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='sexo',
    id_column='sexo_id'
) }}
