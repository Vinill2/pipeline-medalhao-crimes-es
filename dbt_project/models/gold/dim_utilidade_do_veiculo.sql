{{ config(materialized='incremental', unique_key='utilidade_do_veiculo_id') }}

{#
    Dimensao incremental de utilidade_do_veiculo. Mesmo padrao das outras 9 dimensoes: ids nunca
    sao reatribuidos, so valores novos recebem id na proxima execucao.
    Sem cod_incidente/cod_grupo_incidente aqui -- essas duas colunas ainda nao
    foram corrigidas (pendente, conforme combinado).
#}

{{ build_incremental_dimension(
    source_relation=ref('slv_ocorrencias'),
    value_column='utilidade_do_veiculo',
    id_column='utilidade_do_veiculo_id'
) }}
