"""Tests for attribute-based configuration"""
import pytest
import panflute as pf
from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS


def stringify_result(result):
    """Helper to stringify results that might be lists or single elements"""
    if isinstance(result, list):
        return '\n'.join(pf.stringify(elem) for elem in result if elem is not None)
    elif result is not None:
        return pf.stringify(result)
    return ''


class TestAttributeParsing:
    """Tests for parsing code block attributes"""

    def setup_method(self):
        """Clear global state before each test"""
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

    def test_simple_attribute_data_file(self):
        """Test using data= attribute to specify data file"""
        # First define a template
        template_block = pf.CodeBlock(
            text="""---
name: test-template
---
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}""",
            classes=['embedz']
        )
        process_embedz(template_block, pf.Doc())

        # Now use it with data= attribute (this would need actual file, skip for now)
        # Just test attribute parsing works

    def test_attribute_with_template(self):
        """Test using template= attribute with inline data"""
        # Define template
        template_block = pf.CodeBlock(
            text="""---
name: item-list
---
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}""",
            classes=['embedz']
        )
        process_embedz(template_block, pf.Doc())

        # Use template with inline CSV data via attributes
        code_block = pf.CodeBlock(
            text="""name,value
Alice,100
Bob,200""",
            classes=['embedz'],
            attributes=[('as', 'item-list'), ('format', 'csv')]
        )

        result = process_embedz(code_block, pf.Doc())
        result_text = stringify_result(result)

        assert 'Alice' in result_text
        assert '100' in result_text
        assert 'Bob' in result_text
        assert '200' in result_text

    def test_attribute_format_specification(self):
        """Test format= attribute"""
        # Define template
        template_block = pf.CodeBlock(
            text="""---
name: json-template
---
{% for item in data %}
- {{ item.name }}: {{ item.count }}
{% endfor %}""",
            classes=['embedz']
        )
        process_embedz(template_block, pf.Doc())

        # Use with JSON format attribute
        code_block = pf.CodeBlock(
            text="""[
  {"name": "Apple", "count": 10},
  {"name": "Banana", "count": 5}
]""",
            classes=['embedz'],
            attributes=[('as', 'json-template'), ('format', 'json')]
        )

        result = process_embedz(code_block, pf.Doc())
        result_text = stringify_result(result)

        assert 'Apple' in result_text
        assert '10' in result_text
        assert 'Banana' in result_text
        assert '5' in result_text

    def test_attribute_header_boolean(self):
        """Test header= attribute with boolean value"""
        code_block = pf.CodeBlock(
            text="""---
format: csv
---
{% for row in data %}
- Row: {{ row }}
{% endfor %}
---
Alice,100
Bob,200""",
            classes=['embedz'],
            attributes=[('header', 'false')]
        )

        result = process_embedz(code_block, pf.Doc())
        result_text = stringify_result(result)

        # Without header, rows should be lists
        assert 'Alice' in result_text

    def test_yaml_overrides_attributes(self):
        """Test that YAML config takes precedence over attributes"""
        # Simple test: YAML format should override attribute format
        # When both are specified, YAML wins
        code_block = pf.CodeBlock(
            text="""---
format: json
---
{% for item in data %}
- {{ item }}
{% endfor %}
---
["apple", "banana"]""",
            classes=['embedz'],
            attributes=[('format', 'csv')]  # This should be ignored
        )

        result = process_embedz(code_block, pf.Doc())
        result_text = stringify_result(result)

        # Should successfully parse as JSON (not CSV)
        assert 'apple' in result_text
        assert 'banana' in result_text

    def test_name_attribute_for_template_definition(self):
        """Test using name= attribute to define a template"""
        code_block = pf.CodeBlock(
            text="""{% for item in data %}
- {{ item }}
{% endfor %}""",
            classes=['embedz'],
            attributes=[('name', 'simple-list')]
        )

        # Should save template
        process_embedz(code_block, pf.Doc())
        assert 'simple-list' in SAVED_TEMPLATES

    def test_combined_attributes_and_inline_data(self):
        """Test combining multiple attributes with inline data"""
        # Define template
        template_block = pf.CodeBlock(
            text="""---
name: product-list
---
{% for item in data %}
- {{ item.product }}: ${{ item.price }}
{% endfor %}""",
            classes=['embedz']
        )
        process_embedz(template_block, pf.Doc())

        # Use multiple attributes
        code_block = pf.CodeBlock(
            text="""product,price
Widget,19.99
Gadget,29.99""",
            classes=['embedz'],
            attributes=[
                ('as', 'product-list'),
                ('format', 'csv'),
                ('header', 'true')
            ]
        )

        result = process_embedz(code_block, pf.Doc())
        result_text = stringify_result(result)

        assert 'Widget' in result_text
        assert '19.99' in result_text
        assert 'Gadget' in result_text
        assert '29.99' in result_text


class TestAttributeOnlyBlocks:
    """Tests for blocks using only attributes (no YAML)"""

    def setup_method(self):
        """Clear global state before each test"""
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

    def test_data_attribute_with_template(self):
        """Test template with inline data using only attributes"""
        # Define template using name= attribute
        code_block = pf.CodeBlock(
            text="""Hello {% for name in data %}{{ name }}{% endfor %}!""",
            classes=['embedz'],
            attributes=[('name', 'greeting')]
        )

        process_embedz(code_block, pf.Doc())

        # Verify template was saved
        assert 'greeting' in SAVED_TEMPLATES


class TestAttributeEdgeCases:
    """Tests for edge cases and error conditions"""

    def setup_method(self):
        """Clear global state before each test"""
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

    def test_invalid_format_value(self):
        """Test that invalid format value raises error"""
        code_block = pf.CodeBlock(
            text="""---
format: invalid_format
---
{% for item in data %}{{ item }}{% endfor %}
---
test data""",
            classes=['embedz']
        )

        with pytest.raises(ValueError, match="Invalid format"):
            process_embedz(code_block, pf.Doc())

    def test_invalid_format_in_attributes(self):
        """Test that invalid format in attributes raises error"""
        code_block = pf.CodeBlock(
            text="""test data""",
            classes=['embedz'],
            attributes=[('format', 'invalid_format'), ('as', 'foo')]
        )

        # Need to define template first
        SAVED_TEMPLATES['foo'] = '{{ data }}'

        with pytest.raises(ValueError, match="Invalid format"):
            process_embedz(code_block, pf.Doc())

    def test_template_not_found(self):
        """Test that using undefined template raises error"""
        code_block = pf.CodeBlock(
            text="""name,value
Alice,100""",
            classes=['embedz'],
            attributes=[('as', 'nonexistent'), ('format', 'csv')]
        )

        with pytest.raises(ValueError, match="Template 'nonexistent' not found"):
            process_embedz(code_block, pf.Doc())

    def test_header_type_validation(self):
        """Test that header must be boolean"""
        code_block = pf.CodeBlock(
            text="""---
format: csv
header: "not a boolean"
---
{% for row in data %}{{ row }}{% endfor %}
---
a,b,c""",
            classes=['embedz']
        )

        with pytest.raises(TypeError, match="'header' must be a boolean"):
            process_embedz(code_block, pf.Doc())

    def test_boolean_attribute_conversion(self):
        """Test that boolean string attributes are converted properly"""
        # Define template
        template_block = pf.CodeBlock(
            text="""{% for row in data %}{{ row[0] }},{{ row[1] }}{% endfor %}""",
            classes=['embedz'],
            attributes=[('name', 'no-header-template')]
        )
        process_embedz(template_block, pf.Doc())

        # Test with header=false as string
        code_block = pf.CodeBlock(
            text="""Alice,100
Bob,200""",
            classes=['embedz'],
            attributes=[('as', 'no-header-template'), ('format', 'csv'), ('header', 'false')]
        )

        result = process_embedz(code_block, pf.Doc())
        result_text = stringify_result(result)

        # Should work - header="false" converted to boolean False
        assert 'Alice' in result_text
        assert '100' in result_text

    def test_yaml_overrides_attribute_format(self):
        """Test YAML format takes precedence over attribute format"""
        # Define template
        SAVED_TEMPLATES['test'] = '{% for item in data %}{{ item }}{% endfor %}'

        code_block = pf.CodeBlock(
            text="""---
format: json
as: test
---
---
["apple", "banana"]""",
            classes=['embedz'],
            attributes=[('format', 'csv')]  # CSV ignored, YAML format wins
        )

        result = process_embedz(code_block, pf.Doc())
        result_text = stringify_result(result)

        # Should parse as JSON successfully (not CSV)
        assert 'apple' in result_text
        assert 'banana' in result_text

    def test_empty_attributes_dict(self):
        """Test code block with no attributes works normally"""
        code_block = pf.CodeBlock(
            text="""---
format: json
---
{% for item in data %}{{ item }}{% endfor %}
---
["test"]""",
            classes=['embedz'],
            attributes={}
        )

        result = process_embedz(code_block, pf.Doc())
        result_text = stringify_result(result)

        assert 'test' in result_text

    def test_attribute_only_no_template_no_data(self):
        """Test attribute-only block without template or data attribute is valid"""
        # Just format attribute, no data - should save empty template
        code_block = pf.CodeBlock(
            text="""{% for item in data %}{{ item }}{% endfor %}""",
            classes=['embedz'],
            attributes=[('format', 'csv'), ('name', 'test-template')]
        )

        # Should save template even without data
        process_embedz(code_block, pf.Doc())
        assert 'test-template' in SAVED_TEMPLATES
"""Test YAML content without --- delimiters when data + with attributes"""
import pytest
import panflute as pf
from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS
from io import StringIO


def stringify_result(result):
    if isinstance(result, list):
        return '\n'.join(pf.stringify(elem) for elem in result if elem is not None)
    elif result is not None:
        return pf.stringify(result)
    return ''


class TestYAMLWithoutDelimiters:
    def setup_method(self):
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

    def test_data_with_yaml_content_no_delimiters(self):
        """Test data + with attributes with YAML content (no --- delimiters)"""
        # Define template
        SAVED_TEMPLATES['test'] = 'Title: {{ with.title }}, Count: {{ data | length }}'

        # Use template with data attribute and YAML content
        code_block = pf.CodeBlock(
            text="""with:
  title: "Test Title"
  url: "http://example.com" """,
            classes=['embedz'],
            attributes={'data': 'tests/fixtures/sample.csv', 'as': 'test'}
        )

        result = process_embedz(code_block, pf.Doc())
        output = stringify_result(result)

        assert 'Test Title' in output
        assert 'Count: 3' in output

    def test_data_with_invalid_yaml_treated_as_data(self):
        """Test that specifying both data attribute and inline data raises error"""
        # Define template
        SAVED_TEMPLATES['test'] = 'Count: {{ data | length }}'

        # Both data attribute and inline data (should raise error)
        code_block = pf.CodeBlock(
            text="""Alice,100
Bob,200""",
            classes=['embedz'],
            attributes={'data': 'tests/fixtures/sample.csv', 'as': 'test', 'format': 'csv'}
        )

        # Should raise ValueError for mutual exclusivity
        with pytest.raises(ValueError, match="Cannot specify both 'data' attribute and inline data"):
            process_embedz(code_block, pf.Doc())

    def test_yaml_with_format_specification(self):
        """Test YAML content with format specification"""
        SAVED_TEMPLATES['test'] = '{{ data | length }} items'

        code_block = pf.CodeBlock(
            text="""format: json
with:
  debug: true""",
            classes=['embedz'],
            attributes={'data': 'tests/fixtures/sample.json', 'as': 'test'}
        )

        result = process_embedz(code_block, pf.Doc())
        output = stringify_result(result)

        assert '3 items' in output


class TestWithDotNotation:
    """Tests for with.* attribute notation"""

    def setup_method(self):
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

    def test_with_dot_single_variable(self):
        """Test with.key="value" attribute notation"""
        # Define template
        SAVED_TEMPLATES['test'] = 'Title: {{ title }}'

        # Use with.title attribute
        code_block = pf.CodeBlock(
            text='',
            classes=['embedz'],
            attributes={'data': 'tests/fixtures/sample.csv', 'as': 'test', 'with.title': 'My Title'}
        )

        result = process_embedz(code_block, pf.Doc())
        output = stringify_result(result)

        assert 'Title: My Title' in output

    def test_with_dot_multiple_variables(self):
        """Test multiple with.* attributes"""
        SAVED_TEMPLATES['test'] = 'Title: {{ title }}, URL: {{ url }}'

        code_block = pf.CodeBlock(
            text='',
            classes=['embedz'],
            attributes={
                'data': 'tests/fixtures/sample.csv',
                'as': 'test',
                'with.title': 'My Title',
                'with.url': 'http://example.com'
            }
        )

        result = process_embedz(code_block, pf.Doc())
        output = stringify_result(result)

        assert 'Title: My Title' in output
        assert 'URL: http://example.com' in output

    def test_with_dot_accessible_as_with_namespace(self):
        """Test that with.* attributes are accessible as with.key"""
        SAVED_TEMPLATES['test'] = 'Title: {{ with.title }}'

        code_block = pf.CodeBlock(
            text='',
            classes=['embedz'],
            attributes={'data': 'tests/fixtures/sample.csv', 'as': 'test', 'with.title': 'Namespaced'}
        )

        result = process_embedz(code_block, pf.Doc())
        output = stringify_result(result)

        assert 'Title: Namespaced' in output

    def test_yaml_with_overrides_attribute_with(self):
        """Test that YAML with: takes precedence over with.* attributes"""
        SAVED_TEMPLATES['test'] = 'Title: {{ title }}'

        code_block = pf.CodeBlock(
            text="""with:
  title: "YAML Title" """,
            classes=['embedz'],
            attributes={
                'data': 'tests/fixtures/sample.csv',
                'as': 'test',
                'with.title': 'Attribute Title'  # Should be overridden
            }
        )

        result = process_embedz(code_block, pf.Doc())
        output = stringify_result(result)

        # YAML should win
        assert 'Title: YAML Title' in output
        assert 'Attribute Title' not in output

    def test_with_dot_boolean_conversion(self):
        """Test that boolean strings are converted in with.* attributes"""
        SAVED_TEMPLATES['test'] = '{% if debug %}Debug mode{% endif %}'

        code_block = pf.CodeBlock(
            text='',
            classes=['embedz'],
            attributes={'data': 'tests/fixtures/sample.csv', 'as': 'test', 'with.debug': 'true'}
        )

        result = process_embedz(code_block, pf.Doc())
        output = stringify_result(result)

        assert 'Debug mode' in output

    def test_global_dot_notation(self):
        """Test that global.* attribute notation works"""
        # Set global variable via attribute
        code_block1 = pf.CodeBlock(
            text='',
            classes=['embedz'],
            attributes={'global.author': 'John Doe'}
        )
        process_embedz(code_block1, pf.Doc())

        # Use global variable in template
        SAVED_TEMPLATES['test'] = 'Author: {{ author }}'
        code_block2 = pf.CodeBlock(
            text='',
            classes=['embedz'],
            attributes={'data': 'tests/fixtures/sample.csv', 'as': 'test'}
        )

        result = process_embedz(code_block2, pf.Doc())
        output = stringify_result(result)

        assert 'Author: John Doe' in output

    def test_arbitrary_dot_notation(self):
        """Test that arbitrary key.subkey notation creates nested dicts"""
        code_block = pf.CodeBlock(
            text='',
            classes=['embedz'],
            attributes={'custom.field': 'value'}
        )

        from pandoc_embedz.filter import parse_attributes
        config = parse_attributes(code_block)

        assert 'custom' in config
        assert config['custom']['field'] == 'value'
