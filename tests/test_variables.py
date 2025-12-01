"""Tests for variable scoping (local and global)"""
import pytest
import panflute as pf
from pandoc_embedz import filter as filter_module
from pandoc_embedz.filter import process_embedz, GLOBAL_VARS
from pandoc_embedz.config import SAVED_TEMPLATES


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global state before each test"""
    SAVED_TEMPLATES.clear()
    GLOBAL_VARS.clear()
    filter_module.CONTROL_STRUCTURES_PARTS.clear()
    filter_module.GLOBAL_ENV = None
    yield
    SAVED_TEMPLATES.clear()
    GLOBAL_VARS.clear()
    filter_module.CONTROL_STRUCTURES_PARTS.clear()
    filter_module.GLOBAL_ENV = None


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

    def test_use_macro_directly_in_query(self):
        """Test using imported macro directly in query field without global variable"""
        # Define SQL macro
        sql_macro = """{%- macro BETWEEN(start, end) -%}
SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
{%- endmacro -%}"""

        elem1 = pf.CodeBlock(sql_macro, classes=['embedz'], attributes={'name': 'date-macros'})
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Import macro and define date variables
        setup_code = """---
global:
  _import: "{% from 'date-macros' import BETWEEN %}"
  year_start: "2024-01-01"
  year_end: "2024-12-31"
---
"""
        elem2 = pf.CodeBlock(setup_code, classes=['embedz'])
        process_embedz(elem2, doc)

        # Use macro directly in query without storing in global variable
        query_code = """---
format: csv
query: "{{ BETWEEN(year_start, year_end) }}"
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

        elem3 = pf.CodeBlock(query_code, classes=['embedz'])
        result = process_embedz(elem3, doc)

        # Should only include rows within the date range
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # 2024
        assert 'Charlie: 90' in output  # 2024
        assert 'Bob' not in output  # 2023
        assert 'David' not in output  # 2025

    def test_preamble_with_set_and_macro(self):
        """Test preamble section for defining control structures"""
        # Use preamble to define variables and macros
        test_code = """---
preamble: |
  {% set title = 'Annual Report' %}
  {% set year = 2024 %}
  {% macro HELLO(name) %}Hello, {{ name }}!{% endmacro %}

global:
  heading: "# {{ title }} {{ year }}"
  greeting: "{{ HELLO('World') }}"
format: json
---
{% for item in data %}
{{ heading }}
{{ greeting }}
{{ item.name }}
{% endfor %}
---
[{"name": "Test"}]
"""
        elem = pf.CodeBlock(test_code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        # Verify global variables used preamble definitions
        assert 'heading' in GLOBAL_VARS
        assert GLOBAL_VARS['heading'] == '# Annual Report 2024'
        assert 'greeting' in GLOBAL_VARS
        assert GLOBAL_VARS['greeting'] == 'Hello, World!'

        # Verify template rendering
        assert isinstance(result, list)
        assert len(result) > 0

    def test_preamble_invalid_type(self):
        """Test that non-string preamble raises error"""
        test_code = """---
preamble:
  - invalid
  - list
---
"""
        elem = pf.CodeBlock(test_code, classes=['embedz'])
        doc = pf.Doc()

        with pytest.raises(ValueError, match="'preamble' must be a string"):
            process_embedz(elem, doc)

    def test_use_macro_without_explicit_import(self):
        """Test using macro defined in named template without explicit import statement"""
        # Define SQL macro in named template
        sql_macro = """{%- macro BETWEEN(start, end) -%}
SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
{%- endmacro -%}"""

        elem1 = pf.CodeBlock(sql_macro, classes=['embedz'], attributes={'name': 'MACROS'})
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Define global variables WITHOUT explicit import
        # Macro should be available automatically since it's in a named template
        setup_code = """---
global:
  year_start: "2024-01-01"
  year_end: "2024-12-31"
  yearly: "{{ BETWEEN(year_start, year_end) }}"
---
"""
        elem2 = pf.CodeBlock(setup_code, classes=['embedz'])
        process_embedz(elem2, doc)

        # Verify macro was executed in global variable
        assert 'yearly' in GLOBAL_VARS
        assert "SELECT * FROM data WHERE date BETWEEN '2024-01-01' AND '2024-12-31'" in GLOBAL_VARS['yearly']

        # Use macro directly in query without import
        query_code = """---
format: csv
query: "{{ BETWEEN(year_start, year_end) }}"
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

        elem3 = pf.CodeBlock(query_code, classes=['embedz'])
        result = process_embedz(elem3, doc)

        # Should only include rows within the date range
        assert isinstance(result, list)
        assert len(result) > 0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output  # 2024
        assert 'Charlie: 90' in output  # 2024
        assert 'Bob' not in output  # 2023
        assert 'David' not in output  # 2025


class TestGlobalVariablesWithData:
    """Tests for global variables that reference loaded data"""

    def test_global_variable_referencing_data(self):
        """Test global variable can reference loaded data"""
        code = """---
format: csv
global:
  total_count: "{{ data | length }}"
---
Total: {{ total_count }}
---
name,value
Alice,100
Bob,80
Charlie,90"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['total_count'] == '3'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Total: 3' in output

    def test_global_variable_with_data_aggregation(self):
        """Test global variable can aggregate data values"""
        code = """---
format: csv
global:
  total_value: "{{ data | sum(attribute='value') }}"
  average_value: "{{ (data | sum(attribute='value')) / (data | length) }}"
---
Total: {{ total_value }}, Average: {{ average_value }}
---
name,value
Alice,100
Bob,80
Charlie,120"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['total_value'] == '300'
        assert GLOBAL_VARS['average_value'] == '100.0'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Total: 300' in output
        assert 'Average: 100.0' in output

    def test_global_variable_with_data_filter(self):
        """Test global variable can filter data"""
        code = """---
format: csv
global:
  high_value_count: "{{ data | selectattr('value', 'gt', 90) | list | length }}"
---
High value items: {{ high_value_count }}
---
name,value
Alice,100
Bob,80
Charlie,120
David,50"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['high_value_count'] == '2'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'High value items: 2' in output

    def test_global_variable_with_query_result(self):
        """Test global variable can reference query result"""
        code = """---
format: csv
query: SELECT * FROM data WHERE value > 80
global:
  filtered_count: "{{ data | length }}"
---
Filtered count: {{ filtered_count }}
---
name,value
Alice,100
Bob,80
Charlie,120
David,50"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Query filters to Alice(100) and Charlie(120)
        assert GLOBAL_VARS['filtered_count'] == '2'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Filtered count: 2' in output

    def test_global_variable_available_in_subsequent_block(self):
        """Test global variable set from data is available in later blocks"""
        # First block: load data and set global variable
        code1 = """---
format: csv
global:
  report_total: "{{ data | sum(attribute='value') }}"
---
---
name,value
Alice,100
Bob,200"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert GLOBAL_VARS['report_total'] == '300'

        # Second block: use the global variable
        code2 = """---
format: json
---
Report total from previous block: {{ report_total }}
---
[]"""

        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Report total from previous block: 300' in output

    def test_global_variable_with_first_item(self):
        """Test global variable can extract first item from data"""
        code = """---
format: csv
global:
  first_name: "{{ (data | first).name }}"
  first_value: "{{ (data | first).value }}"
---
First: {{ first_name }} ({{ first_value }})
---
name,value
Alice,100
Bob,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['first_name'] == 'Alice'
        assert GLOBAL_VARS['first_value'] == '100'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'First: Alice (100)' in output

    def test_query_uses_global_from_previous_block(self):
        """Test query can use global variables defined in previous block"""
        # First block: define query parameters
        code1 = """---
global:
  min_value: 80
---
"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Second block: use global in query, then set new global from result
        code2 = """---
format: csv
query: SELECT * FROM data WHERE value >= {{ min_value }}
global:
  filtered_total: "{{ data | sum(attribute='value') }}"
---
Filtered total: {{ filtered_total }}
---
name,value
Alice,100
Bob,50
Charlie,80"""

        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        # Query filters to Alice(100) and Charlie(80), sum = 180
        assert GLOBAL_VARS['filtered_total'] == '180'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Filtered total: 180' in output


class TestGlobalBind:
    """Tests for global bind: subsection with type preservation"""

    def test_bind_preserves_dict_type(self):
        """Test bind: preserves dict type from data | first"""
        code = """---
format: csv
global:
  bind:
    first_row: data | first
---
Name: {{ first_row.name }}, Value: {{ first_row.value }}
---
name,value
Alice,100
Bob,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Verify type is dict, not string
        assert isinstance(GLOBAL_VARS['first_row'], dict)
        assert GLOBAL_VARS['first_row']['name'] == 'Alice'
        assert GLOBAL_VARS['first_row']['value'] == 100

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Name: Alice, Value: 100' in output

    def test_bind_preserves_list_type(self):
        """Test bind: preserves list type"""
        code = """---
format: csv
global:
  bind:
    all_rows: data | list
---
Count: {{ all_rows | length }}
---
name,value
Alice,100
Bob,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Verify type is list, not string
        assert isinstance(GLOBAL_VARS['all_rows'], list)
        assert len(GLOBAL_VARS['all_rows']) == 2

    def test_bind_preserves_int_type(self):
        """Test bind: preserves int type from aggregation"""
        code = """---
format: csv
global:
  bind:
    total: data | sum(attribute='value')
    count: data | length
---
Total: {{ total }}, Count: {{ count }}
---
name,value
Alice,100
Bob,80
Charlie,120"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Verify types are int, not string
        assert isinstance(GLOBAL_VARS['total'], (int, float))
        assert GLOBAL_VARS['total'] == 300
        assert isinstance(GLOBAL_VARS['count'], int)
        assert GLOBAL_VARS['count'] == 3

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Total: 300' in output
        assert 'Count: 3' in output

    def test_bind_preserves_none_type(self):
        """Test bind: preserves None when no match found"""
        code = """---
format: csv
global:
  bind:
    no_match: data | selectattr('value', 'gt', 1000) | first | default(none)
---
Has match: {{ no_match is not none }}
---
name,value
Alice,100
Bob,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Verify None is preserved
        assert GLOBAL_VARS['no_match'] is None

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Has match: False' in output

    def test_bind_preserves_bool_type(self):
        """Test bind: preserves bool type from comparison"""
        code = """---
format: csv
global:
  bind:
    has_data: data | length > 0
    is_empty: data | length == 0
---
Has data: {{ has_data }}, Is empty: {{ is_empty }}
---
name,value
Alice,100"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Verify bool types
        assert isinstance(GLOBAL_VARS['has_data'], bool)
        assert GLOBAL_VARS['has_data'] is True
        assert isinstance(GLOBAL_VARS['is_empty'], bool)
        assert GLOBAL_VARS['is_empty'] is False

    def test_bind_with_filtered_list(self):
        """Test bind: with selectattr filter preserves list"""
        code = """---
format: csv
global:
  bind:
    high_values: data | selectattr('value', 'gt', 50) | list
---
High value count: {{ high_values | length }}
First high: {{ high_values[0].name }}
---
name,value
Alice,100
Bob,30
Charlie,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Verify filtered list
        assert isinstance(GLOBAL_VARS['high_values'], list)
        assert len(GLOBAL_VARS['high_values']) == 2
        assert GLOBAL_VARS['high_values'][0]['name'] == 'Alice'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'High value count: 2' in output
        assert 'First high: Alice' in output

    def test_bind_processing_order(self):
        """Test bind: variables are processed in order and can reference earlier ones"""
        code = """---
format: csv
global:
  year: 2024
  date_str: "{{ year }}-01-01"
  bind:
    total: data | sum(attribute='value')
    first: data | first
---
Year: {{ year }}, Date: {{ date_str }}, Total: {{ total }}, First: {{ first.name }}
---
name,value
Alice,100
Bob,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Regular variables are still strings
        assert GLOBAL_VARS['year'] == 2024  # YAML int
        assert GLOBAL_VARS['date_str'] == '2024-01-01'  # template string
        # bind variables preserve types
        assert isinstance(GLOBAL_VARS['total'], (int, float))
        assert isinstance(GLOBAL_VARS['first'], dict)

    def test_bind_available_in_subsequent_block(self):
        """Test bind: variables are available in later blocks"""
        # First block: bind data
        code1 = """---
format: csv
global:
  bind:
    summary: data | first
    total: data | sum(attribute='value')
---
---
name,value
Alice,100
Bob,200"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Verify types
        assert isinstance(GLOBAL_VARS['summary'], dict)
        assert isinstance(GLOBAL_VARS['total'], (int, float))

        # Second block: use bound variables
        code2 = """---
format: json
---
Summary: {{ summary.name }} ({{ summary.value }})
Total: {{ total }}
---
[]"""

        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Summary: Alice (100)' in output
        assert 'Total: 300' in output

    def test_bind_multiline_expression(self):
        """Test bind: with multiline expression"""
        code = """---
format: csv
global:
  bind:
    filtered: |
      data
      | selectattr('value', 'gt', 50)
      | list
---
Filtered count: {{ filtered | length }}
---
name,value
Alice,100
Bob,30
Charlie,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['filtered'], list)
        assert len(GLOBAL_VARS['filtered']) == 2

    def test_bind_as_plain_variable_when_not_dict(self):
        """Test bind: as plain variable when value is not dict"""
        code = """---
global:
  bind: "this is a string"
---
Bind value: {{ bind }}
---
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # When bind value is not dict, it should be treated as regular variable
        assert GLOBAL_VARS['bind'] == 'this is a string'

    def test_bind_can_reference_previous_global(self):
        """Test bind: can reference previously defined global variables"""
        # First block: define threshold
        code1 = """---
global:
  threshold: 60
---
"""
        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Second block: use threshold in bind expression
        code2 = """---
format: csv
global:
  bind:
    filtered: data | selectattr('value', 'gt', threshold) | list
---
Filtered: {{ filtered | length }} items
---
name,value
Alice,100
Bob,50
Charlie,80"""

        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['filtered'], list)
        # Alice(100) and Charlie(80) are > 60
        assert len(GLOBAL_VARS['filtered']) == 2

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Filtered: 2 items' in output


class TestNestedGlobalExpansion:
    """Tests for recursive template expansion in nested global structures"""

    def test_nested_dict_template_expansion(self):
        """Test template expansion in nested dict structure"""
        code = """---
global:
  year: 2024
  report:
    title: "Annual Report {{ year }}"
    period:
      start: "{{ year }}-04-01"
      end: "{{ year + 1 }}-03-31"
---
Title: {{ report.title }}
Period: {{ report.period.start }} to {{ report.period.end }}
---
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['report']['title'] == 'Annual Report 2024'
        assert GLOBAL_VARS['report']['period']['start'] == '2024-04-01'
        assert GLOBAL_VARS['report']['period']['end'] == '2025-03-31'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Title: Annual Report 2024' in output
        assert 'Period: 2024-04-01 to 2025-03-31' in output

    def test_nested_dict_with_bind(self):
        """Test nested dict can reference bind variables"""
        code = """---
format: csv
global:
  bind:
    first_row: data | first
    total: data | sum(attribute='value')
  summary:
    name: "{{ first_row.name }}"
    value: "{{ first_row.value }}"
    total: "{{ total }}"
---
Summary: {{ summary.name }} has {{ summary.value }}, total is {{ summary.total }}
---
name,value
Alice,100
Bob,200
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['summary']['name'] == 'Alice'
        assert GLOBAL_VARS['summary']['value'] == '100'
        assert GLOBAL_VARS['summary']['total'] == '300'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Summary: Alice has 100, total is 300' in output

    def test_deeply_nested_structure(self):
        """Test deeply nested structure expansion"""
        code = """---
global:
  base: 10
  level1:
    value: "{{ base }}"
    level2:
      value: "{{ base * 2 }}"
      level3:
        value: "{{ base * 3 }}"
---
L1: {{ level1.value }}, L2: {{ level1.level2.value }}, L3: {{ level1.level2.level3.value }}
---
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['level1']['value'] == '10'
        assert GLOBAL_VARS['level1']['level2']['value'] == '20'
        assert GLOBAL_VARS['level1']['level2']['level3']['value'] == '30'

    def test_list_in_nested_dict(self):
        """Test template expansion in list within nested dict"""
        code = """---
global:
  year: 2024
  config:
    years:
      - "{{ year - 2 }}"
      - "{{ year - 1 }}"
      - "{{ year }}"
---
Years: {{ config.years | join(', ') }}
---
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['config']['years'] == ['2022', '2023', '2024']

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Years: 2022, 2023, 2024' in output

    def test_nested_dict_available_in_subsequent_block(self):
        """Test nested dict defined in one block is available in later blocks"""
        # First block: define nested structure with bind
        code1 = """---
format: csv
global:
  bind:
    first: data | first
  info:
    name: "{{ first.name }}"
    value: "{{ first.value }}"
---
---
name,value
Alice,100
Bob,200
"""
        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert GLOBAL_VARS['info']['name'] == 'Alice'
        assert GLOBAL_VARS['info']['value'] == '100'

        # Second block: use the nested structure
        code2 = """---
---
Info: {{ info.name }} = {{ info.value }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Info: Alice = 100' in output

    def test_plain_values_in_nested_dict_unchanged(self):
        """Test plain values (no template syntax) are preserved"""
        code = """---
global:
  config:
    name: plain text
    count: 42
    enabled: true
    items:
      - one
      - two
---
Name: {{ config.name }}, Count: {{ config.count }}
---
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['config']['name'] == 'plain text'
        assert GLOBAL_VARS['config']['count'] == 42
        assert GLOBAL_VARS['config']['enabled'] is True
        assert GLOBAL_VARS['config']['items'] == ['one', 'two']


class TestTopLevelBind:
    """Tests for top-level bind: section (outside global:)"""

    def test_top_level_bind_preserves_dict_type(self):
        """Test top-level bind: preserves dict type"""
        code = """---
format: csv
bind:
  first_row: data | first
---
Name: {{ first_row.name }}, Value: {{ first_row.value }}
---
name,value
Alice,100
Bob,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['first_row'], dict)
        assert GLOBAL_VARS['first_row']['name'] == 'Alice'
        assert GLOBAL_VARS['first_row']['value'] == 100

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Name: Alice, Value: 100' in output

    def test_top_level_bind_preserves_int_type(self):
        """Test top-level bind: preserves integer type"""
        code = """---
format: csv
bind:
  total: data | sum(attribute='value')
  count: data | length
---
Total: {{ total }}, Count: {{ count }}
---
name,value
Alice,100
Bob,80
Charlie,20"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['total'], int)
        assert GLOBAL_VARS['total'] == 200
        assert isinstance(GLOBAL_VARS['count'], int)
        assert GLOBAL_VARS['count'] == 3

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Total: 200, Count: 3' in output

    def test_top_level_bind_with_global(self):
        """Test top-level bind: works alongside global:"""
        code = """---
format: csv
global:
  title: "Summary Report"
bind:
  first: data | first
  total: data | sum(attribute='value')
---
{{ title }}: {{ first.name }} (Total: {{ total }})
---
name,value
Alice,100
Bob,200"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['title'] == 'Summary Report'
        assert isinstance(GLOBAL_VARS['first'], dict)
        assert GLOBAL_VARS['first']['name'] == 'Alice'
        assert GLOBAL_VARS['total'] == 300

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Summary Report: Alice (Total: 300)' in output

    def test_top_level_bind_available_in_subsequent_block(self):
        """Test top-level bind variables are available in subsequent blocks"""
        # First block: bind variables
        code1 = """---
format: csv
bind:
  first_row: data | first
  total: data | sum(attribute='value')
---
---
name,value
Alice,100
Bob,200"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert isinstance(GLOBAL_VARS['first_row'], dict)
        assert GLOBAL_VARS['total'] == 300

        # Second block: use bound variables
        code2 = """---
---
First: {{ first_row.name }} ({{ first_row.value }})
Total: {{ total }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'First: Alice (100)' in output
        assert 'Total: 300' in output

    def test_top_level_bind_with_computation(self):
        """Test top-level bind: supports computations with preserved types"""
        code = """---
format: csv
bind:
  first: data | first
  second: data | last
  diff: (data | first).value - (data | last).value
  greater: (data | first).value > (data | last).value
---
Diff: {{ diff }}, First > Last: {{ greater }}
---
name,value
Alice,100
Bob,30"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['diff'] == 70
        assert GLOBAL_VARS['greater'] is True

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Diff: 70' in output
        # Note: > may be escaped to \> in markdown output
        assert 'First' in output and 'Last: True' in output

    def test_global_can_reference_top_level_bind(self):
        """Test global: can reference top-level bind: variables"""
        code = """---
format: csv
bind:
  first: data | first
  total: data | sum(attribute='value')
global:
  summary: "{{ first.name }}: {{ total }}"
---
Summary: {{ summary }}
---
name,value
Alice,100
Bob,30
Charlie,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['first'], dict)
        assert GLOBAL_VARS['total'] == 210
        assert GLOBAL_VARS['summary'] == 'Alice: 210'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Summary: Alice: 210' in output
