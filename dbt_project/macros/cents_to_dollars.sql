{% macro cents_to_dollars(column_name) %}
    {# Convert integer cents to decimal dollars #}
    ({{ column_name }} / 100.0)
{% endmacro %}
