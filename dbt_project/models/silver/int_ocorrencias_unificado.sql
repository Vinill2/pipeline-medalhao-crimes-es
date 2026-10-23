{#
    Etapa 2: une as 18 tabelas stg_* em uma unica tabela de ocorrencias.
    Cada arquivo de origem pode ter mais ou menos colunas -- a uniao e feita
    pelo NOME da coluna (ver macro union_relations_by_name), entao colunas
    ausentes em um arquivo viram NULL nessa linha, sem quebrar o UNION.
#}

{%- set nomes_origem = [
    "homicidio_feminicidio",
    "violencia_domestica",
    "crime_informatico",
    "estelionato_fraude",
    "roubo_celular",
    "roubo_bicicleta",
    "roubo_veiculo",
    "furto_celular",
    "furto_bicicleta",
    "furto_veiculo",
    "roubo_transporte_coletivo",
    "roubo_residencia",
    "roubo_comercio",
    "roubo_pessoa",
    "furto_residencia",
    "furto_transporte_coletivo",
    "furto_comercio",
    "furto_pessoa"
] -%}

{%- set relations = [] -%}
{%- for nome in nomes_origem -%}
    {%- do relations.append(source('silver_raw', 'stg_' ~ nome)) -%}
{%- endfor -%}

{{ union_relations_by_name(relations) }}
