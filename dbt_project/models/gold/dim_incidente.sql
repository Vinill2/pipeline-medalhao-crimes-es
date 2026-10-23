{{ config(materialized='table') }}

{#
    Diferente das outras dimensoes, aqui NAO geramos id novo: cod_incidente e
    cod_grupo_incidente ja vem da origem como identificadores proprios (um id
    unico de tipo_de_incidente e outro de grupo_de_incidente). Por isso essa
    tabela e reconstruida inteira a cada execucao (materialized='table'), sem
    precisar de logica incremental -- os ids nao sao nossos, entao nao ha risco
    de reatribuir algo que ja existia.

    Um mesmo cod_incidente pode aparecer em varias ocorrencias; assumimos que
    tipo_de_incidente (e o grupo associado) sao estaveis por cod_incidente e
    usamos MAX (ignora NULL) para resolver eventual inconsistencia.
#}

select
    cod_incidente,
    max(tipo_de_incidente) as tipo_de_incidente,
    max(cod_grupo_incidente) as cod_grupo_incidente,
    max(grupo_de_incidente) as grupo_de_incidente
from {{ ref('slv_ocorrencias') }}
where nullif(trim(cod_incidente), '') is not null
group by cod_incidente
