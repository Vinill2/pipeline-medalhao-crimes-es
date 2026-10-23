{#
    Tabela fato: uma linha por ocorrencia, so com os ids numericos das dimensoes
    (as colunas de texto originais sao removidas daqui -- elas vivem nas dim_*).
    Demais colunas (datas, horas, no_ocorrencia, idade, cod_incidente, cod_grupo_incidente
    e qualquer outra coluna que não virou dimensao) passam direto.
#}

{% set slv = ref('slv_ocorrencias') %}
{% set colunas_dimensao = [
    'tipo_de_boletim', 'agencia', 'unidade', 'unidade_origem_pc',
    'uf', 'municipio', 'bairro', 'logradouro', 'tipo_de_local',
    'cor', 'meios', 'sexo', 'orientacao_sexual', 'tipo_objeto', 'acao_objeto',
    'tipo', 'marca', 'modelo', 'cor_veiculo', 'utilidade_do_veiculo',
    'tipo_de_incidente', 'grupo_de_incidente', 'tipo_crime'
] %}
{% set colunas_restantes = get_relation_column_names(slv, excluded_columns=colunas_dimensao) %}

select
    {% for coluna in colunas_restantes %}
    s.{{ coluna }},
    {% endfor %}
    dim_tipo_de_boletim.tipo_de_boletim_id,
    dim_agencia.agencia_id,
    dim_unidade.unidade_id,
    dim_unidade_origem_pc.unidade_origem_pc_id,
    dim_uf.uf_id,
    dim_municipio.municipio_id,
    dim_bairro.bairro_id,
    dim_logradouro.logradouro_id,
    dim_tipo_de_local.tipo_de_local_id,
    dim_cor.cor_id,
    dim_meios.meios_id,
    dim_sexo.sexo_id,
    dim_orientacao_sexual.orientacao_sexual_id,
    dim_tipo_objeto.tipo_objeto_id,
    dim_acao_objeto.acao_objeto_id,
    dim_tipo.tipo_id,
    dim_marca.marca_id,
    dim_modelo.modelo_id,
    dim_cor_veiculo.cor_veiculo_id,
    dim_utilidade_do_veiculo.utilidade_do_veiculo_id,
    dim_tipo_crime.tipo_crime_id
from {{ slv }} as s
left join {{ ref('dim_tipo_de_boletim') }} as dim_tipo_de_boletim
    on dim_tipo_de_boletim.tipo_de_boletim = nullif(trim(s.tipo_de_boletim), '')
left join {{ ref('dim_agencia') }} as dim_agencia
    on dim_agencia.agencia = nullif(trim(s.agencia), '')
left join {{ ref('dim_unidade') }} as dim_unidade
    on dim_unidade.unidade = nullif(trim(s.unidade), '')
left join {{ ref('dim_unidade_origem_pc') }} as dim_unidade_origem_pc
    on dim_unidade_origem_pc.unidade_origem_pc = nullif(trim(s.unidade_origem_pc), '')
left join {{ ref('dim_uf') }} as dim_uf
    on dim_uf.uf = nullif(trim(s.uf), '')
left join {{ ref('dim_municipio') }} as dim_municipio
    on dim_municipio.municipio = nullif(trim(s.municipio), '')
left join {{ ref('dim_bairro') }} as dim_bairro
    on dim_bairro.bairro = nullif(trim(s.bairro), '')
left join {{ ref('dim_logradouro') }} as dim_logradouro
    on dim_logradouro.logradouro = nullif(trim(s.logradouro), '')
left join {{ ref('dim_tipo_de_local') }} as dim_tipo_de_local
    on dim_tipo_de_local.tipo_de_local = nullif(trim(s.tipo_de_local), '')
left join {{ ref('dim_cor') }} as dim_cor
    on dim_cor.cor = nullif(trim(s.cor), '')
left join {{ ref('dim_meios') }} as dim_meios
    on dim_meios.meios = nullif(trim(s.meios), '')
left join {{ ref('dim_sexo') }} as dim_sexo
    on dim_sexo.sexo = nullif(trim(s.sexo), '')
left join {{ ref('dim_orientacao_sexual') }} as dim_orientacao_sexual
    on dim_orientacao_sexual.orientacao_sexual = nullif(trim(s.orientacao_sexual), '')
left join {{ ref('dim_tipo_objeto') }} as dim_tipo_objeto
    on dim_tipo_objeto.tipo_objeto = nullif(trim(s.tipo_objeto), '')
left join {{ ref('dim_acao_objeto') }} as dim_acao_objeto
    on dim_acao_objeto.acao_objeto = nullif(trim(s.acao_objeto), '')
left join {{ ref('dim_tipo') }} as dim_tipo
    on dim_tipo.tipo = nullif(trim(s.tipo), '')
left join {{ ref('dim_marca') }} as dim_marca
    on dim_marca.marca = nullif(trim(s.marca), '')
left join {{ ref('dim_modelo') }} as dim_modelo
    on dim_modelo.modelo = nullif(trim(s.modelo), '')
left join {{ ref('dim_cor_veiculo') }} as dim_cor_veiculo
    on dim_cor_veiculo.cor_veiculo = nullif(trim(s.cor_veiculo), '')
left join {{ ref('dim_utilidade_do_veiculo') }} as dim_utilidade_do_veiculo
    on dim_utilidade_do_veiculo.utilidade_do_veiculo = nullif(trim(s.utilidade_do_veiculo), '')
left join {{ ref('dim_tipo_crime') }} as dim_tipo_crime
    on dim_tipo_crime.tipo_crime = nullif(trim(s.tipo_crime), '')
