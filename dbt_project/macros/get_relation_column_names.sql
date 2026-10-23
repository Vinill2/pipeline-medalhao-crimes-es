{% macro get_relation_column_names(relation, excluded_columns=[]) %}
    {%- set column_names = [] -%}
    {%- if execute -%}
        {%- set relation_columns = adapter.get_columns_in_relation(relation) -%}
        {%- for column in relation_columns -%}
            {%- if column.name not in excluded_columns -%}
                {%- do column_names.append(column.name) -%}
            {%- endif -%}
        {%- endfor -%}
    {%- endif -%}
    {{ return(column_names) }}
{% endmacro %}
