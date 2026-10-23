{#
    Entrega final da Silver:
    - no_ocorrencia: inteiro (ja deduplicado na etapa anterior)
    - hora_do_fato / hora_de_criacao: so mantem valores no formato HH:MM:SS
    - data_do_fato / data_de_criacao: convertidas para data ISO
    - idade: inteiro, "S/I" vira NULL
    - cor (<- cutis), sexo (<- genero, pega so depois do " - "), tipo_de_local (<- tipo_local):
      fusao de colunas sinonimas, prioridade pra coluna de destino.
    - tipo_crime: busca o "titulo" do arquivo de origem em config/sources.json
      (carregado como tabela ref_fonte), via join por nome_tabela.

    IMPORTANTE: a limpeza das colunas de dimensao (maiusculo, sem acento, valores tipo
    "S/I"/"indeterminado" virando NULL) NAO acontece aqui em SQL -- acontece antes, em
    Python (src/reader.py: clean_dataframe_dimension_columns), na carga de cada stg_*.
    Tentamos fazer isso em SQL primeiro, mas o encadeamento de REPLACE() pra tirar
    acento estourava o limite de profundidade do parser do SQLite. Por isso os valores
    que chegam aqui (agencia, municipio, cor, etc.) ja vem maiusculos/limpos; so a
    uniao de sinonimos (cutis->cor, genero->sexo, tipo_local->tipo_de_local, titulo->tipo_crime)
    e feita aqui, porque depende de mais de uma coluna/tabela ao mesmo tempo.
    tipo_crime especificamente precisa do upper()/trim() aqui porque titulo vem direto
    da tabela ref_fonte (fora do pipeline de limpeza em Python), nao tem acento complexo
    o bastante pra estourar o parser.

    - tipificacao, tipo_de_envolvimento, cod_envolvido, cod_seq, e as colunas sinonimas
      ja fundidas (data, hora, cutis, genero, tipo_local, nome_tabela) saem do resultado.
    - todo o restante vira TEXT.
#}

{% set dedup = ref('int_ocorrencias_dedup') %}

{% set colunas_dimensao_simples = [
    'tipo_de_boletim', 'agencia', 'unidade', 'unidade_origem_pc',
    'uf', 'municipio', 'bairro', 'logradouro',
    'meios', 'orientacao_sexual', 'tipo_objeto', 'acao_objeto',
    'tipo', 'marca', 'modelo', 'cor_veiculo', 'utilidade_do_veiculo',
    'tipo_de_incidente', 'grupo_de_incidente'
] %}

{% set colunas_especiais = [
    'no_ocorrencia', 'hora_do_fato', 'hora_de_criacao', 'data_do_fato', 'data_de_criacao',
    'idade', 'cor', 'sexo', 'tipo_de_local',
    'data', 'hora', 'cutis', 'genero', 'tipo_local', 'nome_tabela',
    'tipificacao', 'tipo_de_envolvimento', 'cod_envolvido', 'cod_seq'
] + colunas_dimensao_simples %}

{% set colunas_restantes = get_relation_column_names(dedup, excluded_columns=colunas_especiais) %}

select
    cast(nullif(trim(o.no_ocorrencia), '') as integer) as no_ocorrencia,

    {{ clean_time_column("coalesce(nullif(trim(o.hora_do_fato), ''), nullif(trim(o.hora), ''))") }} as hora_do_fato,
    {{ clean_time_column('o.hora_de_criacao') }} as hora_de_criacao,

    {{ to_iso_date("coalesce(nullif(trim(o.data_do_fato), ''), nullif(trim(o.data), ''))") }} as data_do_fato,
    {{ to_iso_date('o.data_de_criacao') }} as data_de_criacao,

    case
        when upper(trim(o.idade)) in ('S/I', '') then null
        else cast(o.idade as integer)
    end as idade,

    -- ja chegam limpos (maiusculo/sem sentinela) do Python; so falta unir sinonimos
    coalesce(o.cor, o.cutis) as cor,
    coalesce(
        case
            when o.genero like '% - %' then substr(o.genero, instr(o.genero, ' - ') + 3)
            else o.genero
        end,
        o.sexo
    ) as sexo,
    coalesce(o.tipo_de_local, o.tipo_local) as tipo_de_local,

    nullif(upper(trim(rf.titulo)), '') as tipo_crime

    {% for coluna in colunas_dimensao_simples %}
    , o.{{ coluna }}
    {% endfor %}

    {% for coluna in colunas_restantes %}
    , cast(o.{{ coluna }} as text) as {{ coluna }}
    {% endfor %}

from {{ dedup }} as o
left join {{ source('silver_raw', 'ref_fonte') }} as rf
    on o.nome_tabela = rf.nome_tabela
