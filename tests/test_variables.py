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
bind:
  first_row: data | first
  total: data | sum(attribute='value')
global:
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
bind:
  first: data | first
global:
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

    def test_top_level_bind_nested_structure(self):
        """Test top-level bind: with nested dict structure"""
        code = """---
format: csv
bind:
  first: data | first
  info:
    name: first.name
    value: first.value
    doubled: first.value * 2
---
Name: {{ info.name }}, Value: {{ info.value }}, Doubled: {{ info.doubled }}
---
name,value
Alice,100
Bob,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['info'], dict)
        assert GLOBAL_VARS['info']['name'] == 'Alice'
        assert GLOBAL_VARS['info']['value'] == 100
        assert GLOBAL_VARS['info']['doubled'] == 200

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Name: Alice, Value: 100, Doubled: 200' in output

    def test_top_level_bind_deeply_nested(self):
        """Test top-level bind: with deeply nested structure preserving types"""
        code = """---
format: csv
bind:
  first: data | first
  report:
    summary:
      name: first.name
      stats:
        value: first.value
        is_high: first.value > 50
---
High value: {{ report.summary.stats.is_high }}
---
name,value
Alice,100
Bob,80"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['report']['summary']['name'] == 'Alice'
        assert GLOBAL_VARS['report']['summary']['stats']['value'] == 100
        assert GLOBAL_VARS['report']['summary']['stats']['is_high'] is True

    def test_bind_preserves_list_type(self):
        """Test bind: preserves list type"""
        code = """---
format: csv
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
        assert isinstance(GLOBAL_VARS['all_rows'], list)
        assert len(GLOBAL_VARS['all_rows']) == 2

    def test_bind_preserves_none_type(self):
        """Test bind: preserves None when no match found"""
        code = """---
format: csv
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
        assert GLOBAL_VARS['no_match'] is None

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Has match: False' in output

    def test_bind_preserves_bool_type(self):
        """Test bind: preserves bool type from comparison"""
        code = """---
format: csv
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
        assert isinstance(GLOBAL_VARS['has_data'], bool)
        assert GLOBAL_VARS['has_data'] is True
        assert isinstance(GLOBAL_VARS['is_empty'], bool)
        assert GLOBAL_VARS['is_empty'] is False

    def test_bind_with_filtered_list(self):
        """Test bind: with selectattr filter preserves list"""
        code = """---
format: csv
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
        assert isinstance(GLOBAL_VARS['high_values'], list)
        assert len(GLOBAL_VARS['high_values']) == 2
        assert GLOBAL_VARS['high_values'][0]['name'] == 'Alice'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'High value count: 2' in output
        assert 'First high: Alice' in output

    def test_bind_multiline_expression(self):
        """Test bind: with multiline expression"""
        code = """---
format: csv
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

    def test_bind_can_reference_previous_global(self):
        """Test bind: can reference previously defined global variables (from earlier block)"""
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


class TestBindDotNotation:
    """Tests for bind: with dot notation to set nested values"""

    def test_bind_dot_notation_sets_nested_value(self):
        """Test bind: key with dot notation sets nested value in existing dict"""
        code = """---
format: csv
bind:
  record: data | first
  record.memo: "'added memo'"
---
Name: {{ record.name }}, Memo: {{ record.memo }}
---
name,value
Alice,100"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['record'], dict)
        assert GLOBAL_VARS['record']['name'] == 'Alice'
        assert GLOBAL_VARS['record']['value'] == 100
        assert GLOBAL_VARS['record']['memo'] == 'added memo'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Name: Alice, Memo: added memo' in output

    def test_bind_dot_notation_creates_intermediate_dicts(self):
        """Test bind: dot notation creates intermediate dicts if not present"""
        code = """---
format: csv
bind:
  result.stats.count: data | length
  result.stats.total: data | sum(attribute='value')
---
Count: {{ result.stats.count }}, Total: {{ result.stats.total }}
---
name,value
Alice,100
Bob,200"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['result'], dict)
        assert isinstance(GLOBAL_VARS['result']['stats'], dict)
        assert GLOBAL_VARS['result']['stats']['count'] == 2
        assert GLOBAL_VARS['result']['stats']['total'] == 300

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Count: 2, Total: 300' in output

    def test_bind_dot_notation_add_to_existing_dict(self):
        """Test bind: dot notation adds key to existing dict"""
        code = """---
format: csv
bind:
  first: data | first
  first.doubled: first.value * 2
  first.label: "'Primary'"
---
{{ first.name }}: {{ first.value }} (x2={{ first.doubled }}, label={{ first.label }})
---
name,value
Alice,100
Bob,200"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['first']['name'] == 'Alice'
        assert GLOBAL_VARS['first']['value'] == 100
        assert GLOBAL_VARS['first']['doubled'] == 200
        assert GLOBAL_VARS['first']['label'] == 'Primary'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100 (x2=200, label=Primary)' in output

    def test_bind_dot_notation_deeply_nested(self):
        """Test bind: dot notation with deeply nested path"""
        code = """---
format: csv
bind:
  report.summary.data.first: data | first
  report.summary.data.count: data | length
---
First: {{ report.summary.data.first.name }}, Count: {{ report.summary.data.count }}
---
name,value
Alice,100
Bob,200
Charlie,300"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['report']['summary']['data']['first']['name'] == 'Alice'
        assert GLOBAL_VARS['report']['summary']['data']['count'] == 3

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'First: Alice, Count: 3' in output

    def test_bind_dot_notation_available_in_subsequent_block(self):
        """Test bind: with dot notation is available in later blocks"""
        # First block: set nested value
        code1 = """---
format: csv
bind:
  record: data | first
  record.note: "'First record'"
---
---
name,value
Alice,100"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert GLOBAL_VARS['record']['name'] == 'Alice'
        assert GLOBAL_VARS['record']['note'] == 'First record'

        # Second block: use the nested value
        code2 = """---
---
Record: {{ record.name }} - {{ record.note }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Record: Alice - First record' in output

    def test_bind_dot_notation_error_on_non_dict_parent(self):
        """Test bind: dot notation raises error when parent is not dict"""
        code = """---
format: csv
bind:
  count: data | length
  count.child: "'should fail'"
---
---
name,value
Alice,100"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        with pytest.raises(ValueError, match="Cannot set 'count.child': 'count' is not a dictionary"):
            process_embedz(elem, doc)

    def test_bind_dot_notation_with_japanese_keys(self):
        """Test bind: dot notation works with Japanese keys"""
        code = """---
format: csv
bind:
  今年度: data | first
  今年度.説明: "'今年度のデータ'"
---
今年度: {{ 今年度.name }}, 説明: {{ 今年度.説明 }}
---
name,value
Alice,100"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['今年度']['name'] == 'Alice'
        assert GLOBAL_VARS['今年度']['説明'] == '今年度のデータ'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '今年度: Alice' in output
        assert '説明: 今年度のデータ' in output


class TestGlobalDotNotation:
    """Tests for global: with dot notation to set nested values"""

    def test_global_dot_notation_adds_to_bind_dict(self):
        """Test global: dot notation adds key to dict created by bind:"""
        code = """---
format: csv
bind:
  record: data | first
global:
  record.memo: Added by global
---
Name: {{ record.name }}, Memo: {{ record.memo }}
---
name,value
Alice,100"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['record']['name'] == 'Alice'
        assert GLOBAL_VARS['record']['value'] == 100
        assert GLOBAL_VARS['record']['memo'] == 'Added by global'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Name: Alice, Memo: Added by global' in output

    def test_global_dot_notation_creates_intermediate_dicts(self):
        """Test global: dot notation creates intermediate dicts"""
        code = """---
global:
  config.settings.name: Test App
  config.settings.version: 1.0
---
App: {{ config.settings.name }} v{{ config.settings.version }}
---
"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['config']['settings']['name'] == 'Test App'
        assert GLOBAL_VARS['config']['settings']['version'] == 1.0

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'App: Test App v1.0' in output

    def test_global_dot_notation_with_bind_nested_structure(self):
        """Test global: dot notation works with bind: nested structure"""
        code = """---
format: csv
bind:
  stats:
    count: data | length
    total: data | sum(attribute='value')
global:
  stats.label: Summary Statistics
---
{{ stats.label }}: Count={{ stats.count }}, Total={{ stats.total }}
---
name,value
Alice,100
Bob,200"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['stats']['count'] == 2
        assert GLOBAL_VARS['stats']['total'] == 300
        assert GLOBAL_VARS['stats']['label'] == 'Summary Statistics'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Summary Statistics: Count=2, Total=300' in output

    def test_global_dot_notation_error_on_non_dict_parent(self):
        """Test global: dot notation raises error when parent is not dict"""
        code = """---
format: csv
bind:
  count: data | length
global:
  count.child: should fail
---
---
name,value
Alice,100"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        with pytest.raises(ValueError, match="Cannot set 'count.child': 'count' is not a dictionary"):
            process_embedz(elem, doc)


class TestToDictFilter:
    """Tests for to_dict custom Jinja2 filter"""

    def test_to_dict_basic(self):
        """Test to_dict filter converts list of dicts to keyed dict"""
        code = """---
format: csv
bind:
  by_name: data | to_dict('name')
---
Alice value: {{ by_name['Alice'].value }}
Bob value: {{ by_name['Bob'].value }}
---
name,value
Alice,100
Bob,200"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['by_name'], dict)
        assert 'Alice' in GLOBAL_VARS['by_name']
        assert 'Bob' in GLOBAL_VARS['by_name']
        assert GLOBAL_VARS['by_name']['Alice']['value'] == 100
        assert GLOBAL_VARS['by_name']['Bob']['value'] == 200

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice value: 100' in output
        assert 'Bob value: 200' in output

    def test_to_dict_with_numeric_key(self):
        """Test to_dict filter with numeric key field"""
        code = """---
format: csv
bind:
  by_year: data | to_dict('year')
---
2023 value: {{ by_year[2023].value }}
2024 value: {{ by_year[2024].value }}
---
year,value
2023,100
2024,200"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['by_year'], dict)
        assert 2023 in GLOBAL_VARS['by_year']
        assert 2024 in GLOBAL_VARS['by_year']
        assert GLOBAL_VARS['by_year'][2023]['value'] == 100
        assert GLOBAL_VARS['by_year'][2024]['value'] == 200

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '2023 value: 100' in output
        assert '2024 value: 200' in output

    def test_to_dict_with_variable_access(self):
        """Test to_dict filter with variable key access"""
        code = """---
format: csv
with:
  target_year: 2024
bind:
  by_year: data | to_dict('year')
  target_data: by_year[target_year]
---
Target year value: {{ target_data.value }}
---
year,value
2023,100
2024,200
2025,300"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['target_data'], dict)
        assert GLOBAL_VARS['target_data']['value'] == 200

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Target year value: 200' in output

    def test_to_dict_with_global_fiscal_year(self):
        """Test to_dict filter with fiscal_year global variable"""
        # First block: set fiscal_year
        code1 = """---
global:
  fiscal_year: 2024
---
"""
        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Second block: use fiscal_year to access dict
        code2 = """---
format: csv
bind:
  by_year: data | to_dict('year')
  current: by_year[fiscal_year]
  previous: by_year[fiscal_year - 1]
---
Current: {{ current.value }}, Previous: {{ previous.value }}
---
year,value
2023,100
2024,200
2025,300"""

        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['current']['value'] == 200
        assert GLOBAL_VARS['previous']['value'] == 100

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Current: 200, Previous: 100' in output

    def test_to_dict_with_japanese_key(self):
        """Test to_dict filter with Japanese key field"""
        code = """---
format: csv
bind:
  年度別: data | to_dict('年度')
---
2023年度: {{ 年度別[2023].報告件数 }}件
---
年度,報告件数,調整件数
2023,65690,19720
2024,70000,20000"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert isinstance(GLOBAL_VARS['年度別'], dict)
        assert 2023 in GLOBAL_VARS['年度別']
        assert GLOBAL_VARS['年度別'][2023]['報告件数'] == 65690

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '2023年度: 65690件' in output

    def test_to_dict_available_in_subsequent_block(self):
        """Test to_dict result is available in subsequent blocks"""
        # First block: create dict
        code1 = """---
format: csv
bind:
  items: data | to_dict('id')
---
---
id,name
1,Alice
2,Bob"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert isinstance(GLOBAL_VARS['items'], dict)
        assert GLOBAL_VARS['items'][1]['name'] == 'Alice'

        # Second block: use the dict
        code2 = """---
---
Item 1: {{ items[1].name }}
Item 2: {{ items[2].name }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Item 1: Alice' in output
        assert 'Item 2: Bob' in output

    def test_to_dict_error_on_non_list(self):
        """Test to_dict filter raises error on non-list input"""
        code = """---
format: json
bind:
  bad: data | to_dict('key')
---
---
{"not": "a list"}"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        with pytest.raises(TypeError, match="to_dict expects a list"):
            process_embedz(elem, doc)

    def test_to_dict_strict_by_default(self):
        """Test to_dict filter raises on duplicate keys by default"""
        code = """---
format: csv
bind:
  by_name: data | to_dict('name')
---
{{ by_name }}
---
name,value
Alice,100
Alice,200"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        with pytest.raises(ValueError, match="to_dict: duplicate key 'Alice' in field 'name'"):
            process_embedz(elem, doc)

    def test_to_dict_strict_false_allows_duplicates(self):
        """Test to_dict filter with strict=False allows duplicate keys"""
        code = """---
format: csv
bind:
  by_name: data | to_dict('name', strict=False)
---
Alice value: {{ by_name['Alice'].value }}
---
name,value
Alice,100
Alice,200"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Last value wins
        assert GLOBAL_VARS['by_name']['Alice']['value'] == 200

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice value: 200' in output

    def test_to_dict_transpose(self):
        """Test to_dict filter with transpose=True for dual access"""
        code = """---
format: csv
bind:
  by_year: data | to_dict('year', transpose=True)
---
Row access: {{ by_year[2023].value }}
Column access: {{ by_year.value[2023] }}
---
year,value,count
2023,100,10
2024,200,20"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Row access still works
        assert 2023 in GLOBAL_VARS['by_year']
        assert GLOBAL_VARS['by_year'][2023]['value'] == 100
        # Column access now available
        assert 'value' in GLOBAL_VARS['by_year']
        assert 'count' in GLOBAL_VARS['by_year']
        assert GLOBAL_VARS['by_year']['value'][2023] == 100
        assert GLOBAL_VARS['by_year']['value'][2024] == 200
        assert GLOBAL_VARS['by_year']['count'][2023] == 10

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Row access: 100' in output
        assert 'Column access: 100' in output

    def test_to_dict_transpose_without_key_column(self):
        """Test that transpose excludes the key column from column-keyed dicts"""
        code = """---
format: csv
bind:
  by_year: data | to_dict('year', transpose=True)
---
Check: {{ by_year.value[2023] }}
---
year,value
2023,100
2024,200"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem, doc)

        # 'year' should not be in the column-keyed dicts (it's the key)
        assert 'year' not in GLOBAL_VARS['by_year'] or not isinstance(GLOBAL_VARS['by_year'].get('year'), dict)
        # 'value' should be there
        assert 'value' in GLOBAL_VARS['by_year']
        assert isinstance(GLOBAL_VARS['by_year']['value'], dict)


class TestRaiseFilter:
    """Tests for raise custom Jinja2 filter"""

    def test_raise_filter_basic(self):
        """Test raise filter raises ValueError with message"""
        code = """---
---
{{ "Test error message" | raise }}
---
dummy"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        with pytest.raises(ValueError, match="Test error message"):
            process_embedz(elem, doc)

    def test_raise_filter_conditional(self):
        """Test raise filter with conditional check"""
        code = """---
with:
  label: ""
---
{%- if not label -%}
{{ "label is required" | raise }}
{%- endif -%}
Value: {{ label }}
---
dummy"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        with pytest.raises(ValueError, match="label is required"):
            process_embedz(elem, doc)

    def test_raise_filter_not_triggered(self):
        """Test raise filter is not triggered when condition is false"""
        code = """---
with:
  label: "test"
---
{%- if not label -%}
{{ "label is required" | raise }}
{%- endif -%}
Value: {{ label }}
---
dummy"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Value: test' in output

    def test_raise_filter_with_is_not_defined(self):
        """Test raise filter with 'is not defined' check"""
        code = """---
---
{%- if undefined_var is not defined -%}
{{ "undefined_var is required" | raise }}
{%- endif -%}
---
dummy"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        with pytest.raises(ValueError, match="undefined_var is required"):
            process_embedz(elem, doc)


class TestAliasFeature:
    """Tests for alias: feature"""

    def test_alias_basic(self):
        """Test alias adds alternative key to dicts"""
        code = """---
format: csv
bind:
  item:
    ラベル: |-
      "テスト項目"
    value: 100
alias:
  のアレ: ラベル
---
{{ item.のアレ }}: {{ item.value }}
---
name,value
dummy,0"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert 'ラベル' in GLOBAL_VARS['item']
        assert 'のアレ' in GLOBAL_VARS['item']
        assert GLOBAL_VARS['item']['のアレ'] == 'テスト項目'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'テスト項目: 100' in output

    def test_alias_nested(self):
        """Test alias works on nested dicts"""
        code = """---
format: csv
bind:
  parent:
    ラベル: |-
      "親項目"
    child:
      ラベル: |-
        "子項目"
alias:
  のアレ: ラベル
---
{{ parent.のアレ }} > {{ parent.child.のアレ }}
---
name,value
dummy,0"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['parent']['のアレ'] == '親項目'
        assert GLOBAL_VARS['parent']['child']['のアレ'] == '子項目'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '親項目' in output and '子項目' in output

    def test_alias_does_not_overwrite(self):
        """Test alias does not overwrite existing key"""
        code = """---
format: csv
bind:
  item:
    ラベル: |-
      "元の値"
    のアレ: |-
      "既存の値"
alias:
  のアレ: ラベル
---
{{ item.のアレ }}
---
name,value
dummy,0"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        # Should keep the existing value, not overwrite with alias
        assert GLOBAL_VARS['item']['のアレ'] == '既存の値'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '既存の値' in output

    def test_alias_multiple(self):
        """Test multiple aliases"""
        code = """---
format: csv
bind:
  item:
    label: |-
      "Item Label"
    description: |-
      "Item Description"
alias:
  ラベル: label
  説明: description
---
{{ item.ラベル }}: {{ item.説明 }}
---
name,value
dummy,0"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['item']['ラベル'] == 'Item Label'
        assert GLOBAL_VARS['item']['説明'] == 'Item Description'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Item Label: Item Description' in output

    def test_alias_available_in_subsequent_block(self):
        """Test aliases are available in subsequent blocks"""
        # First block: define with alias
        code1 = """---
format: csv
bind:
  item:
    ラベル: |-
      "テスト"
alias:
  のアレ: ラベル
---
---
name,value
dummy,0"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert GLOBAL_VARS['item']['のアレ'] == 'テスト'

        # Second block: use the alias
        code2 = """---
---
{{ item.のアレ }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'テスト' in output

    def test_alias_with_real_data(self):
        """Test alias with real incident-like data structure"""
        code = """---
format: csv
bind:
  インシデント:
    ラベル: |-
      "インシデント件数"
    今年度: 26365
    報告:
      ラベル: |-
        "報告件数"
      今年度: 65690
alias:
  のアレ: ラベル
---
{{ インシデント.のアレ }}は{{ インシデント.今年度 }}件、{{ インシデント.報告.のアレ }}は{{ インシデント.報告.今年度 }}件
---
name,value
dummy,0"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert GLOBAL_VARS['インシデント']['のアレ'] == 'インシデント件数'
        assert GLOBAL_VARS['インシデント']['報告']['のアレ'] == '報告件数'

        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'インシデント件数は26365件' in output
        assert '報告件数は65690件' in output


class TestDataVariableReference:
    """Tests for data= referencing GLOBAL_VARS variables"""

    def test_data_references_bind_list(self):
        """Test data= can reference a list from bind:"""
        # First block: create data variable
        code1 = """---
format: csv
bind:
  my_data: data | list
---
---
name,value
Alice,100
Bob,200"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert isinstance(GLOBAL_VARS['my_data'], list)
        assert len(GLOBAL_VARS['my_data']) == 2

        # Second block: reference the variable with data=
        code2 = """---
---
{% for item in data %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': 'my_data'})
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output
        assert 'Bob: 200' in output

    def test_data_references_bind_dict(self):
        """Test data= can reference a dict from bind:"""
        # First block: create data variable as dict
        code1 = """---
format: csv
bind:
  by_year: data | to_dict('year')
---
---
year,value
2023,100
2024,200"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert isinstance(GLOBAL_VARS['by_year'], dict)

        # Second block: reference the dict variable with data=
        code2 = """---
---
2023: {{ data[2023].value }}
2024: {{ data[2024].value }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': 'by_year'})
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '2023: 100' in output
        assert '2024: 200' in output

    def test_data_with_file_path_still_loads_file(self):
        """Test data= with path-like value loads file (not variable)"""
        # First block: create variable that happens to have file-like name
        code1 = """---
format: json
bind:
  test_data: data | list
---
---
[{"name": "FromVar"}]"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Referencing with ./test_data should try to load file (and fail)
        # Since it's a path, it won't look up GLOBAL_VARS
        code2 = """---
format: json
---
{{ data }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': './nonexistent'})

        with pytest.raises((FileNotFoundError, ValueError)):
            process_embedz(elem2, doc)

    def test_data_with_extension_loads_file(self):
        """Test data= with extension loads file (not variable)"""
        # Create variable named like a file
        code1 = """---
global:
  test: ignored
bind:
  data_csv: data | list
---
---
"""
        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # data.csv should try to load file (has extension)
        code2 = """---
---
{{ data }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': 'data.csv'})

        with pytest.raises((FileNotFoundError, ValueError)):
            process_embedz(elem2, doc)

    def test_data_variable_not_found_falls_back_to_file(self):
        """Test data= with non-existent variable tries to load as file"""
        code = """---
---
{{ data }}
---
"""
        elem = pf.CodeBlock(code, classes=['embedz'], attributes={'data': 'nonexistent_var'})
        doc = pf.Doc()

        # Should try to load as file and fail
        with pytest.raises((FileNotFoundError, ValueError)):
            process_embedz(elem, doc)

    def test_data_variable_with_template(self):
        """Test data= variable works with template (as=)"""
        # Define template
        template_code = """{% for item in data %}
- {{ item.name }}
{% endfor %}"""

        elem1 = pf.CodeBlock(template_code, classes=['embedz'], attributes={'define': 'item-list'})
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Create data variable
        code2 = """---
format: csv
bind:
  items: data | list
---
---
name,value
Alice,100
Bob,200"""

        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        process_embedz(elem2, doc)

        # Use template with variable data
        code3 = """---
---
---
"""
        elem3 = pf.CodeBlock(code3, classes=['embedz'], attributes={'data': 'items', 'as': 'item-list'})
        result = process_embedz(elem3, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice' in output
        assert 'Bob' in output

    def test_data_variable_ignores_string_type(self):
        """Test data= ignores string-type global variables"""
        # Create a string global variable
        code1 = """---
global:
  my_string: just a string value
---
"""
        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert GLOBAL_VARS['my_string'] == 'just a string value'

        # Try to use it as data - should fail since strings are not dict/list
        code2 = """---
---
{{ data }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': 'my_string'})

        # Should try to load as file (string type is ignored)
        with pytest.raises((FileNotFoundError, ValueError)):
            process_embedz(elem2, doc)

    def test_data_variable_with_yaml_config(self):
        """Test data= variable specified in YAML config"""
        # First block: create data variable
        code1 = """---
format: csv
bind:
  report_data: data | list
---
---
name,value
Alice,100
Bob,200"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Second block: reference via YAML data:
        code2 = """---
data: report_data
---
{% for item in data %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output
        assert 'Bob: 200' in output

    def test_data_variable_with_inline_data_raises_error(self):
        """Test data= variable with inline data raises error"""
        # First block: create data variable
        code1 = """---
format: csv
bind:
  my_data: data | list
---
---
name,value
Alice,100"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Second block: try to use both variable and inline data
        code2 = """---
data: my_data
---
{{ data }}
---
name,value
Bob,200"""

        elem2 = pf.CodeBlock(code2, classes=['embedz'])

        with pytest.raises(ValueError, match="Cannot specify both data= variable reference and inline data"):
            process_embedz(elem2, doc)

    def test_data_variable_dot_notation(self):
        """Test data= with dot notation for nested access"""
        # First block: create transposed data
        code1 = """---
format: csv
bind:
  by_year: data | to_dict('year', transpose=True)
---
---
year,value,count
2023,100,10
2024,200,20"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert isinstance(GLOBAL_VARS['by_year'], dict)
        assert 'value' in GLOBAL_VARS['by_year']

        # Second block: use dot notation to access nested dict
        code2 = """---
---
2023: {{ data[2023] }}
2024: {{ data[2024] }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': 'by_year.value'})
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '2023: 100' in output
        assert '2024: 200' in output

    def test_data_variable_dot_notation_deep(self):
        """Test data= with multi-level dot notation"""
        # First block: create nested structure using global (not bind)
        # bind tries to evaluate values as expressions, global preserves them
        code1 = """---
global:
  root:
    level1:
      level2:
        items:
          - name: Alice
            value: 100
          - name: Bob
            value: 200
---
"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert isinstance(GLOBAL_VARS['root']['level1']['level2']['items'], list)

        # Second block: use deep dot notation
        code2 = """---
---
{% for item in data %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': 'root.level1.level2.items'})
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Alice: 100' in output
        assert 'Bob: 200' in output

    def test_data_variable_dot_notation_not_found(self):
        """Test data= with dot notation falls back to file when not found"""
        # Create a variable
        code1 = """---
bind:
  my_var:
    existing_key: value
---
"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Reference non-existent nested key - should fall back to file loading
        code2 = """---
---
{{ data }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': 'my_var.nonexistent'})

        with pytest.raises((FileNotFoundError, ValueError)):
            process_embedz(elem2, doc)

    def test_data_variable_explicit_file_path(self):
        """Test data= with ./ prefix forces file loading"""
        # Create variable that could conflict
        code1 = """---
bind:
  some_data:
    value: from_variable
---
"""

        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # ./some_data should force file loading even though variable exists
        code2 = """---
---
{{ data }}
---
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': './some_data'})

        with pytest.raises((FileNotFoundError, ValueError)):
            process_embedz(elem2, doc)

    def test_data_variable_with_query(self):
        """Test that query can be applied to variable data"""
        # First block: bind raw data to variable
        code1 = """---
format: csv
bind:
  raw_data: data
---
---
name,category,value
Alice,A,100
Bob,B,200
Charlie,A,150
David,B,50
"""
        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert 'raw_data' in GLOBAL_VARS
        assert len(GLOBAL_VARS['raw_data']) == 4

        # Second block: apply query to variable data
        code2 = """---
query: |
  SELECT category, SUM(value) as total
  FROM data
  GROUP BY category
  ORDER BY category
---
{% for row in data -%}
{{ row.category }}: {{ row.total }}
{% endfor %}
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': 'raw_data'})
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'A: 250' in output  # Alice(100) + Charlie(150)
        assert 'B: 250' in output  # Bob(200) + David(50)

    def test_data_variable_dict_with_query(self):
        """Test that query can be applied to dict variable (from to_dict)"""
        # First block: bind data as dict using to_dict
        code1 = """---
format: csv
bind:
  by_name: data | to_dict(key='name')
---
---
name,value
Alice,100
Bob,200
"""
        elem1 = pf.CodeBlock(code1, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        assert 'by_name' in GLOBAL_VARS
        assert isinstance(GLOBAL_VARS['by_name'], dict)

        # Second block: apply query to dict variable (values are extracted)
        code2 = """---
query: |
  SELECT SUM(value) as total FROM data
---
Total: {{ data[0].total }}
"""
        elem2 = pf.CodeBlock(code2, classes=['embedz'], attributes={'data': 'by_name'})
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Total: 300' in output  # 100 + 200


class TestRegexReplaceFilter:
    """Tests for regex_replace custom Jinja2 filter"""

    def test_regex_replace_basic(self):
        """Test basic regex replacement"""
        code = """---
---
{{ "Hello World" | regex_replace("World", "Universe") }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Hello Universe' in output

    def test_regex_replace_pattern(self):
        """Test regex pattern replacement"""
        code = """---
---
{{ "ansible" | regex_replace("^a.*i(.*)$", "a\\\\1") }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'able' in output

    def test_regex_replace_remove_chars(self):
        """Test removing characters with empty replacement"""
        code = """---
---
{{ "Hello（World）" | regex_replace("[（）]", "") }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'HelloWorld' in output

    def test_regex_replace_ignorecase(self):
        """Test case-insensitive replacement"""
        code = """---
---
{{ "Hello WORLD" | regex_replace("world", "Universe", ignorecase=true) }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Hello Universe' in output

    def test_regex_replace_multiline(self):
        """Test multiline mode"""
        code = """---
---
{{ "foo\\nbar\\nbaz" | regex_replace("^b", "B", multiline=true) }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Bar' in output
        assert 'Baz' in output

    def test_regex_replace_count(self):
        """Test count parameter to limit replacements"""
        code = """---
---
{{ "foo=bar=baz" | regex_replace("=", ":", count=1) }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'foo:bar=baz' in output

    def test_regex_replace_unicode_word(self):
        """Test removing non-word Unicode characters"""
        code = """---
---
{{ "フィッシング（TOP5）" | regex_replace("\\\\W", "") }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'フィッシングTOP5' in output

    def test_regex_replace_unicode_property(self):
        """Test Unicode property support (requires regex module)"""
        from pandoc_embedz.filter import REGEX_MODULE
        if REGEX_MODULE != 'regex':
            pytest.skip("regex module not installed")

        code = """---
---
{{ "Hello（World）" | regex_replace("\\\\p{Ps}|\\\\p{Pe}", "") }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'HelloWorld' in output


class TestRegexSearchFilter:
    """Tests for regex_search custom Jinja2 filter"""

    def test_regex_search_basic(self):
        """Test basic regex search"""
        code = """---
---
{{ "Hello World" | regex_search("World") }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'World' in output

    def test_regex_search_no_match(self):
        """Test regex search with no match returns empty string"""
        code = """---
---
[{{ "Hello World" | regex_search("Foo") }}]
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '[]' in output or '\\[\\]' in output

    def test_regex_search_pattern(self):
        """Test regex search with pattern alternation"""
        code = """---
---
{{ "備考: 保留中です" | regex_search("保留|済|喪中") }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '保留' in output

    def test_regex_search_ignorecase(self):
        """Test case-insensitive search"""
        code = """---
---
{{ "Hello WORLD" | regex_search("world", ignorecase=true) }}
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'WORLD' in output

    def test_regex_search_in_loop(self):
        """Test regex search in a loop for skip control"""
        code = """---
format: csv
---
{% for row in data %}
{% if row["備考"]|regex_search("保留|済|喪中") %}SKIP{% else %}OK{% endif %}
{% endfor %}
---
No,備考
1,保留中
2,通常
3,喪中
"""
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        output = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'SKIP' in output
        assert 'OK' in output
