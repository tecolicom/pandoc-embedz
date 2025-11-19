"""Tests for variable scoping (local and global)"""
import pytest
import panflute as pf
from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global state before each test"""
    SAVED_TEMPLATES.clear()
    GLOBAL_VARS.clear()
    yield
    SAVED_TEMPLATES.clear()
    GLOBAL_VARS.clear()


class TestLocalVariables:
    """Tests for local variable scoping"""

    def test_local_variables_in_template(self):
        code = """---
format: json
with:
  threshold: 90
  label: "High"
---
{% for item in data %}
{% if item.value > threshold %}
- {{ label }}: {{ item.name }}
{% endif %}
{% endfor %}
---
[{"name": "Arthur", "value": 100}, {"name": "Ford", "value": 85}]"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)

    def test_local_variables_accessible_as_local_dot(self):
        code = """---
format: json
with:
  threshold: 90
---
{% for item in data %}
{% if item.value > with.threshold %}
- {{ item.name }}
{% endif %}
{% endfor %}
---
[{"name": "Arthur", "value": 100}]"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)


class TestGlobalVariables:
    """Tests for global variable scoping"""

    def test_set_global_variables(self):
        code = """---
global:
  threshold: 90
  title: "Test Report"
---
"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        # No output, but globals should be set
        assert result == []
        assert GLOBAL_VARS['threshold'] == 90
        assert GLOBAL_VARS['title'] == "Test Report"

    def test_use_global_variables(self):
        # First, set global variables
        set_code = """---
global:
  threshold: 90
---
"""
        elem1 = pf.CodeBlock(set_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Then use them
        use_code = """---
format: json
---
{% for item in data %}
{% if item.value > threshold %}
- {{ item.name }}
{% endif %}
{% endfor %}
---
[{"name": "Arthur", "value": 100}, {"name": "Ford", "value": 85}]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)

    def test_global_variables_accessible_as_global_dot(self):
        # Set global
        set_code = """---
global:
  threshold: 90
---
"""
        elem1 = pf.CodeBlock(set_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use with global.threshold
        use_code = """---
format: json
---
{% for item in data %}
{% if item.value > global.threshold %}
- {{ item.name }}
{% endif %}
{% endfor %}
---
[{"name": "Arthur", "value": 100}]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)


class TestVariablePrecedence:
    """Tests for local vs global variable precedence"""

    def test_local_overrides_global(self):
        # Set global threshold
        set_code = """---
global:
  threshold: 50
---
"""
        elem1 = pf.CodeBlock(set_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use local threshold (should override)
        use_code = """---
format: json
with:
  threshold: 90
---
Threshold: {{ threshold }}
---
[]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        # The rendered result should use local threshold (90, not 50)

    def test_global_available_when_no_local(self):
        # Set global
        set_code = """---
global:
  author: "Arthur"
---
"""
        elem1 = pf.CodeBlock(set_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use without local override
        use_code = """---
format: json
---
Author: {{ author }}
---
[]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)


class TestDataVariable:
    """Tests for data variable accessibility"""

    def test_data_accessible_directly(self):
        code = """---
format: json
---
{% for item in data %}
- {{ item.name }}
{% endfor %}
---
[{"name": "Arthur"}, {"name": "Ford"}]"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)


class TestQueryTemplateExpansion:
    """Tests for query template variable expansion"""

    def test_query_with_global_variable_interpolation(self):
        """Test SQL query with global variable interpolation"""
        # Define global variables
        setup_code = """---
global:
  start_date: '2024-01-01'
  end_date: '2024-12-31'
---
"""
        elem1 = pf.CodeBlock(setup_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use global variables in query
        query_code = """---
format: csv
query: SELECT * FROM data WHERE date >= '{{ global.start_date }}' AND date <= '{{ global.end_date }}'
---
{% for row in data -%}
{{ row.name }}: {{ row.value }}
{% endfor %}
---
name,date,value
Alice,2024-06-15,100
Bob,2023-12-01,80
Charlie,2024-03-20,90
David,2025-01-01,70"""

        elem2 = pf.CodeBlock(query_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        # Should only include rows within the date range
        assert isinstance(result, list)
        assert len(result) > 0

        # Convert to string and check
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # 2024-06-15 is within range
        assert 'Charlie: 90' in output  # 2024-03-20 is within range
        assert 'Bob' not in output  # 2023-12-01 is outside range
        assert 'David' not in output  # 2025-01-01 is outside range

    def test_query_as_complete_global_variable(self):
        """Test using complete SQL query from global variable"""
        # Define query as global variable
        setup_code = """---
global:
  value_filter: SELECT * FROM data WHERE value > 50
---
"""
        elem1 = pf.CodeBlock(setup_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use complete query from global
        query_code = """---
format: csv
query: "{{ global.value_filter }}"
---
{% for row in data -%}
{{ row.name }}: {{ row.value }}
{% endfor %}
---
name,value
Alice,100
Bob,30
Charlie,90"""

        elem2 = pf.CodeBlock(query_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        # Should only include rows where value > 50
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # value > 50
        assert 'Charlie: 90' in output  # value > 50
        assert 'Bob' not in output  # value = 30, not > 50

    def test_query_with_with_variable(self):
        """Test SQL query with with variable"""
        query_code = """---
format: csv
with:
  min_value: 60
query: SELECT * FROM data WHERE value >= {{ min_value }}
---
{% for row in data -%}
{{ row.name }}: {{ row.value }}
{% endfor %}
---
name,value
Alice,100
Bob,50
Charlie,90"""

        elem = pf.CodeBlock(query_code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        # Should only include rows where value >= 60
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # value >= 60
        assert 'Charlie: 90' in output  # value >= 60
        assert 'Bob' not in output  # value = 50, not >= 60

    def test_query_with_global_variable_without_prefix(self):
        """Test SQL query with global variable without prefix"""
        # Define global variables
        setup_code = """---
global:
  min_value: 60
---
"""
        elem1 = pf.CodeBlock(setup_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use global variable in query without prefix
        query_code = """---
format: csv
query: SELECT * FROM data WHERE value >= {{ min_value }}
---
{% for row in data -%}
{{ row.name }}: {{ row.value }}
{% endfor %}
---
name,value
Alice,100
Bob,50
Charlie,90"""

        elem2 = pf.CodeBlock(query_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        # Should only include rows where value >= 60
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # value >= 60
        assert 'Charlie: 90' in output  # value >= 60
        assert 'Bob' not in output  # value = 50, not >= 60

    def test_query_without_template_unchanged(self):
        """Test that queries without template syntax are not processed"""
        query_code = """---
format: csv
query: SELECT * FROM data WHERE value > 50
---
{% for row in data -%}
{{ row.name }}: {{ row.value }}
{% endfor %}
---
name,value
Alice,100
Bob,30"""

        elem = pf.CodeBlock(query_code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        # Should work normally
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output

    def test_nested_global_variables(self):
        """Test global variables that reference other global variables"""
        # Define nested global variables
        setup_code = """---
global:
  start_date: '2024-01-01'
  end_date: '2024-12-31'
  period_filter: SELECT * FROM data WHERE date BETWEEN '{{ global.start_date }}' AND '{{ global.end_date }}'
---
"""
        elem1 = pf.CodeBlock(setup_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use nested variable in query
        query_code = """---
format: csv
query: "{{ global.period_filter }}"
---
{% for row in data -%}
{{ row.name }}: {{ row.value }}
{% endfor %}
---
name,date,value
Alice,2024-06-15,100
Bob,2023-12-01,80
Charlie,2024-03-20,90
David,2025-01-01,70"""

        elem2 = pf.CodeBlock(query_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        # Should only include rows within the date range
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # 2024
        assert 'Charlie: 90' in output  # 2024
        assert 'Bob' not in output  # 2023
        assert 'David' not in output  # 2025

    def test_multi_level_nested_global_variables(self):
        """Test multiple levels of global variable nesting"""
        # Define multi-level nested variables
        setup_code = """---
global:
  year: '2024'
  start_date: '{{ global.year }}-01-01'
  end_date: '{{ global.year }}-12-31'
  date_filter: date BETWEEN '{{ global.start_date }}' AND '{{ global.end_date }}'
  value_filter: value > 50
  combined_query: SELECT * FROM data WHERE {{ global.date_filter }} AND {{ global.value_filter }}
---
"""
        elem1 = pf.CodeBlock(setup_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use multi-level nested query
        query_code = """---
format: csv
query: "{{ global.combined_query }}"
---
{% for row in data -%}
{{ row.name }}: {{ row.value }}
{% endfor %}
---
name,date,value
Alice,2024-06-15,100
Bob,2023-12-01,80
Charlie,2024-03-20,90
David,2025-01-01,70
Eve,2024-08-10,30"""

        elem2 = pf.CodeBlock(query_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        # Should only include 2024 rows with value > 50
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # 2024, value > 50
        assert 'Charlie: 90' in output  # 2024, value > 50
        assert 'Bob' not in output  # 2023
        assert 'David' not in output  # 2025
        assert 'Eve' not in output  # 2024 but value = 30

    def test_nested_global_variables_without_prefix(self):
        """Test nested global variables can reference other variables without prefix"""
        # Define nested global variables using variables without prefix
        setup_code = """---
global:
  year: 2024
  start_date: "{{ year }}-01-01"
  end_date: "{{ year }}-12-31"
  date_filter: date BETWEEN '{{ start_date }}' AND '{{ end_date }}'
---
"""
        elem1 = pf.CodeBlock(setup_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Verify variables were expanded correctly
        assert GLOBAL_VARS['year'] == 2024
        assert GLOBAL_VARS['start_date'] == '2024-01-01'
        assert GLOBAL_VARS['end_date'] == '2024-12-31'
        assert GLOBAL_VARS['date_filter'] == "date BETWEEN '2024-01-01' AND '2024-12-31'"

        # Use nested variable in query without prefix
        query_code = """---
format: csv
query: "SELECT * FROM data WHERE {{ date_filter }}"
---
{% for row in data -%}
{{ row.name }}: {{ row.value }}
{% endfor %}
---
name,date,value
Alice,2024-06-15,100
Bob,2023-12-01,80
Charlie,2024-03-20,90
David,2025-01-01,70"""

        elem2 = pf.CodeBlock(query_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        # Should only include rows within the date range
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # 2024
        assert 'Charlie: 90' in output  # 2024
        assert 'Bob' not in output  # 2023
        assert 'David' not in output  # 2025


class TestMacroSharing:
    """Tests for macro sharing across global variables using template imports"""

    def test_import_macro_from_named_template(self):
        """Test importing macro from named template into global variables"""
        # Define macro in named template
        macro_def = """{%- macro HELLO(name) -%}
Hello, {{ name }}!
{%- endmacro -%}"""

        elem1 = pf.CodeBlock(macro_def, classes=['embedz'], attributes={'name': 'greetings'})
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Import and use macro in global variables
        setup_code = """---
global:
  user_name: "World"
  _import: "{% from 'greetings' import HELLO %}"
  greeting: "{{ HELLO(user_name) }}"
---
"""
        elem2 = pf.CodeBlock(setup_code, classes=['embedz'])
        process_embedz(elem2, doc)

        # Verify macro was executed and result stored
        assert 'greeting' in GLOBAL_VARS
        assert GLOBAL_VARS['greeting'].strip() == "Hello, World!"

    def test_import_sql_macro_for_query_building(self):
        """Test importing SQL macro for building queries"""
        # Define SQL macro
        sql_macro = """{%- macro BETWEEN(start, end) -%}
SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
{%- endmacro -%}"""

        elem1 = pf.CodeBlock(sql_macro, classes=['embedz'], attributes={'name': 'sql-macros'})
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Import and use macro to build queries
        setup_code = """---
global:
  fiscal_year: 2024
  start_date: "{{ fiscal_year }}-04-01"
  end_date: "{{ fiscal_year + 1 }}-03-31"
  _import: "{% from 'sql-macros' import BETWEEN %}"
  yearly_query: "{{ BETWEEN(start_date, end_date) }}"
---
"""
        elem2 = pf.CodeBlock(setup_code, classes=['embedz'])
        process_embedz(elem2, doc)

        # Verify query was generated correctly
        assert 'yearly_query' in GLOBAL_VARS
        expected_query = "SELECT * FROM data WHERE date BETWEEN '2024-04-01' AND '2025-03-31'"
        assert GLOBAL_VARS['yearly_query'].strip() == expected_query

    def test_import_multiple_macros(self):
        """Test importing multiple macros from same template"""
        # Define multiple macros
        macros_def = """{%- macro ADD(a, b) -%}
{{ a + b }}
{%- endmacro -%}

{%- macro MULTIPLY(a, b) -%}
{{ a * b }}
{%- endmacro -%}"""

        elem1 = pf.CodeBlock(macros_def, classes=['embedz'], attributes={'name': 'math'})
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Import and use multiple macros
        setup_code = """---
global:
  x: 10
  y: 5
  _import: "{% from 'math' import ADD, MULTIPLY %}"
  sum: "{{ ADD(x, y) }}"
  product: "{{ MULTIPLY(x, y) }}"
---
"""
        elem2 = pf.CodeBlock(setup_code, classes=['embedz'])
        process_embedz(elem2, doc)

        # Verify both macros worked
        assert GLOBAL_VARS['sum'].strip() == "15"
        assert GLOBAL_VARS['product'].strip() == "50"

    def test_macro_with_nested_variables(self):
        """Test macro using nested global variables"""
        # Define macro
        macro_def = """{%- macro RANGE(start, end) -%}
{{ start }} to {{ end }}
{%- endmacro -%}"""

        elem1 = pf.CodeBlock(macro_def, classes=['embedz'], attributes={'name': 'formatters'})
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use macro with nested variable references
        setup_code = """---
global:
  year: 2024
  q1_start: "{{ year }}-01-01"
  q1_end: "{{ year }}-03-31"
  _import: "{% from 'formatters' import RANGE %}"
  q1_range: "{{ RANGE(q1_start, q1_end) }}"
---
"""
        elem2 = pf.CodeBlock(setup_code, classes=['embedz'])
        process_embedz(elem2, doc)

        # Verify nested variables were resolved before macro execution
        assert GLOBAL_VARS['q1_range'].strip() == "2024-01-01 to 2024-03-31"

    def test_use_imported_macro_in_query(self):
        """Test using imported macro in SQL query with actual data"""
        # Define SQL macro
        sql_macro = """{%- macro WHERE_GREATER(field, value) -%}
{{ field }} > {{ value }}
{%- endmacro -%}"""

        elem1 = pf.CodeBlock(sql_macro, classes=['embedz'], attributes={'name': 'sql-helpers'})
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Import macro and build query
        setup_code = """---
global:
  threshold: 60
  _import: "{% from 'sql-helpers' import WHERE_GREATER %}"
  filter_condition: "{{ WHERE_GREATER('value', threshold) }}"
---
"""
        elem2 = pf.CodeBlock(setup_code, classes=['embedz'])
        process_embedz(elem2, doc)

        # Use generated condition in actual query
        query_code = """---
format: csv
query: SELECT * FROM data WHERE {{ filter_condition }}
---
{% for row in data -%}
{{ row.name }}: {{ row.value }}
{% endfor %}
---
name,value
Alice,100
Bob,50
Charlie,90"""

        elem3 = pf.CodeBlock(query_code, classes=['embedz'])
        result = process_embedz(elem3, doc)

        # Verify query executed correctly
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # value > 60
        assert 'Charlie: 90' in output  # value > 60
        assert 'Bob' not in output  # value = 50, not > 60

    def test_preserve_intentional_whitespace(self):
        """Test that intentional leading/trailing spaces are preserved"""
        setup_code = """---
global:
  prefix: "  "
  suffix: "  "
  value: "{{ prefix }}Hello{{ suffix }}"
---
"""
        elem = pf.CodeBlock(setup_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem, doc)

        # Verify intentional spaces are preserved
        assert GLOBAL_VARS['prefix'] == '  '
        assert GLOBAL_VARS['suffix'] == '  '
        assert GLOBAL_VARS['value'] == '  Hello  '

    def test_preserve_whitespace_with_macro_import(self):
        """Test that intentional spaces are preserved even with macro imports"""
        # Define macro
        macro_def = """{%- macro WRAP(text) -%}
[{{ text }}]
{%- endmacro -%}"""

        elem1 = pf.CodeBlock(macro_def, classes=['embedz'], attributes={'name': 'wrappers'})
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use macro with intentional spaces
        setup_code = """---
global:
  _import: "{% from 'wrappers' import WRAP %}"
  prefix: "  "
  value: "{{ prefix }}Hello"
  wrapped: "{{ WRAP(value) }}"
---
"""
        elem2 = pf.CodeBlock(setup_code, classes=['embedz'])
        process_embedz(elem2, doc)

        # Verify spaces are preserved
        assert GLOBAL_VARS['prefix'] == '  '
        assert GLOBAL_VARS['value'] == '  Hello'
        assert GLOBAL_VARS['wrapped'] == '[  Hello]'
