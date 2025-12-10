"""Tests for attribute-based configuration"""
import pytest
import panflute as pf
from pandoc_embedz.filter import process_embedz, GLOBAL_VARS
from pandoc_embedz.config import SAVED_TEMPLATES


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

    def test_define_attribute_for_template_definition(self):
        """Test using define= attribute to define a template"""
        code_block = pf.CodeBlock(
            text="""{% for item in data %}
- {{ item }}
{% endfor %}""",
            classes=['embedz'],
            attributes=[('define', 'simple-list')]
        )

        # Should save template
        process_embedz(code_block, pf.Doc())
        assert 'simple-list' in SAVED_TEMPLATES

    def test_combined_attributes_and_inline_data(self):
        """Test combining multiple attributes with inline data"""
        # Define template
        template_block = pf.CodeBlock(
            text="""---
define: product-list
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
        # Define template using define= attribute
        code_block = pf.CodeBlock(
            text="""Hello {% for name in data %}{{ name }}{% endfor %}!""",
            classes=['embedz'],
            attributes=[('define', 'greeting')]
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

    def test_ssv_columns_attribute_as_string(self):
        """Test that columns attribute (string from attributes) is converted to int"""
        code_block = pf.CodeBlock(
            text="""ID Name Description
1 Alice Software engineer
2 Bob Project manager with team""",
            classes=['embedz'],
            attributes=[('format', 'ssv'), ('columns', '3')]  # columns as string
        )

        result = process_embedz(code_block, pf.Doc())
        result_text = stringify_result(result)

        # Should parse correctly with spaces in Description
        assert 'Software engineer' in result_text
        assert 'Project manager with team' in result_text

    def test_ssv_columns_invalid_value_raises_error(self):
        """Test that invalid columns value raises clear error"""
        code_block = pf.CodeBlock(
            text="""ID Name Description
1 Alice Test""",
            classes=['embedz'],
            attributes=[('format', 'ssv'), ('columns', 'invalid')]
        )

        with pytest.raises(ValueError, match="'columns' must be an integer"):
            process_embedz(code_block, pf.Doc())


"""Test YAML content without --- delimiters when data + with attributes"""
import pytest
import panflute as pf
from pandoc_embedz.filter import process_embedz, GLOBAL_VARS
from pandoc_embedz.config import SAVED_TEMPLATES
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

        from pandoc_embedz.config import parse_attributes
        config = parse_attributes(code_block)

        assert 'custom' in config
        assert config['custom']['field'] == 'value'


class TestDeprecatedNameParameter:
    """Tests for backward compatibility with deprecated 'name' parameter"""
    
    def setup_method(self):
        """Clear global state before each test"""
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()
    
    def test_name_parameter_yaml_still_works(self, capsys):
        """Deprecated 'name' parameter in YAML should still work with warning"""
        code = """---
name: test-template
---
{% for row in data %}
- {{ row }}
{% endfor %}"""
        
        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)
        
        # Template should be saved
        assert 'test-template' in SAVED_TEMPLATES
        # Should return empty (no data)
        assert result == []
        
        # Check for deprecation warning
        captured = capsys.readouterr()
        assert "deprecated" in captured.err.lower()
        assert "define" in captured.err.lower()
    
    def test_name_attribute_still_works(self, capsys):
        """Deprecated 'name' attribute should still work with warning"""
        elem = pf.CodeBlock(
            text="Template content",
            classes=['embedz'],
            attributes=[('name', 'attr-template')]
        )
        
        process_embedz(elem, pf.Doc())
        
        # Template should be saved
        assert 'attr-template' in SAVED_TEMPLATES
        
        # Check for deprecation warning
        captured = capsys.readouterr()
        assert "deprecated" in captured.err.lower()
    
    def test_name_template_is_saved_correctly(self, capsys):
        """Template defined with deprecated 'name' is saved and can be referenced"""
        # Define template with deprecated 'name'
        define_code = """---
name: legacy-template
---
Template content here"""

        elem1 = pf.CodeBlock(define_code, classes=['embedz'])
        process_embedz(elem1, pf.Doc())

        # Verify template is saved with correct content
        assert 'legacy-template' in SAVED_TEMPLATES
        assert 'Template content here' in SAVED_TEMPLATES['legacy-template']

        # Should have warning from definition
        captured = capsys.readouterr()
        assert "deprecated" in captured.err.lower()
        assert "define" in captured.err.lower()


class TestTemplateParameterAlias:
    """Tests for 'template' parameter as preferred alias for 'as'"""

    def setup_method(self):
        """Clear global state before each test"""
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

    def test_template_parameter_yaml(self, capsys):
        """'template' parameter in YAML should work without warning"""
        # Define template
        define_code = """---
define: test-template
---
{% for row in data %}
- {{ row.name }}
{% endfor %}"""

        elem1 = pf.CodeBlock(define_code, classes=['embedz'])
        process_embedz(elem1, pf.Doc())

        # Use template with 'template:' parameter
        use_code = """---
template: test-template
format: json
---
---
[{"name": "apple"}, {"name": "banana"}]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem2, doc)

        # Should render successfully
        assert result is not None
        result_text = pf.stringify(pf.Doc(*result))
        assert 'apple' in result_text
        assert 'banana' in result_text

        # Should NOT have any deprecation warning
        captured = capsys.readouterr()
        assert "deprecated" not in captured.err.lower()

    def test_template_attribute(self, capsys):
        """'template=' attribute should work without warning"""
        # Define template
        elem1 = pf.CodeBlock(
            text="Template: {{ data[0] }}",
            classes=['embedz'],
            attributes=[('define', 'simple')]
        )
        process_embedz(elem1, pf.Doc())

        # Use template with 'template=' attribute
        elem2 = pf.CodeBlock(
            text='---\nformat: json\n---\n---\n["test"]',
            classes=['embedz'],
            attributes=[('template', 'simple')]
        )
        doc = pf.Doc()
        result = process_embedz(elem2, doc)

        # Should render successfully
        assert result is not None
        result_text = pf.stringify(pf.Doc(*result))
        assert 'Template: test' in result_text

        # Should NOT have any deprecation warning
        captured = capsys.readouterr()
        assert "deprecated" not in captured.err.lower()

    def test_as_still_works(self, capsys):
        """'as' parameter should continue to work without deprecation"""
        # Define template
        define_code = """---
define: legacy-template
---
Result: {{ data[0] }}"""

        elem1 = pf.CodeBlock(define_code, classes=['embedz'])
        process_embedz(elem1, pf.Doc())

        # Use with 'as:' parameter (old style)
        use_code = """---
as: legacy-template
format: json
---
---
["value"]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem2, doc)

        # Should work
        assert result is not None
        result_text = pf.stringify(pf.Doc(*result))
        assert 'Result: value' in result_text

        # 'as' should NOT be deprecated (no warning)
        captured = capsys.readouterr()
        assert "deprecated" not in captured.err.lower()

    def test_template_and_as_conflict(self):
        """Using both 'template' and 'as' should raise error"""
        code = """---
template: template1
as: template2
---"""

        elem = pf.CodeBlock(code, classes=['embedz'])

        # Should raise ValueError about conflicting parameters
        with pytest.raises(ValueError) as excinfo:
            process_embedz(elem, pf.Doc())

        assert "conflicting" in str(excinfo.value).lower() or "both" in str(excinfo.value).lower()


class TestMultiDocumentYAML:
    """Tests for multi-document YAML config files"""

    def setup_method(self):
        """Clear global state before each test"""
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

    def test_load_multi_document_yaml(self, tmp_path):
        """Test loading YAML file with multiple documents"""
        from pandoc_embedz.config import load_config_file

        config_file = tmp_path / "multi.yaml"
        config_file.write_text("""---
global:
  今年度: 2023
---
global:
  前年度: 2022
bind:
  test: "'value'"
---
""", encoding='utf-8')

        result = load_config_file(str(config_file))

        # Both globals should be merged
        assert 'global' in result
        assert result['global']['今年度'] == 2023
        assert result['global']['前年度'] == 2022
        # bind from second doc should be present
        assert 'bind' in result
        assert result['bind']['test'] == "'value'"

    def test_multi_document_deep_merge(self, tmp_path):
        """Test that nested dicts are deep merged across documents"""
        from pandoc_embedz.config import load_config_file

        config_file = tmp_path / "deep.yaml"
        config_file.write_text("""---
global:
  settings:
    name: Test
    version: 1
---
global:
  settings:
    author: John
---
""")

        result = load_config_file(str(config_file))

        # settings should have all three keys
        assert result['global']['settings']['name'] == 'Test'
        assert result['global']['settings']['version'] == 1
        assert result['global']['settings']['author'] == 'John'

    def test_multi_document_later_overrides_earlier(self, tmp_path):
        """Test that later documents override earlier ones for same keys"""
        from pandoc_embedz.config import load_config_file

        config_file = tmp_path / "override.yaml"
        config_file.write_text("""---
global:
  value: first
---
global:
  value: second
---
""")

        result = load_config_file(str(config_file))

        # Later value should win
        assert result['global']['value'] == 'second'

    def test_single_document_still_works(self, tmp_path):
        """Test that single document YAML still works"""
        from pandoc_embedz.config import load_config_file

        config_file = tmp_path / "single.yaml"
        config_file.write_text("""global:
  today: 2023
  quarter: 4
""")

        result = load_config_file(str(config_file))

        assert result['global']['today'] == 2023
        assert result['global']['quarter'] == 4

    def test_empty_documents_ignored(self, tmp_path):
        """Test that empty documents are ignored"""
        from pandoc_embedz.config import load_config_file

        config_file = tmp_path / "empty.yaml"
        config_file.write_text("""---
---
global:
  value: test
---
---
""")

        result = load_config_file(str(config_file))

        assert result['global']['value'] == 'test'

    def test_multi_document_with_different_sections(self, tmp_path):
        """Test multi-document with different section types"""
        from pandoc_embedz.config import load_config_file

        config_file = tmp_path / "sections.yaml"
        config_file.write_text("""---
# First document: preamble and global
preamble: |
  {% macro test() %}Hello{% endmacro %}
global:
  greeting: "{{ test() }}"
---
# Second document: bind section
bind:
  data_value: 100 + 200
---
# Third document: alias
alias:
  のアレ: ラベル
---
""", encoding='utf-8')

        result = load_config_file(str(config_file))

        assert 'preamble' in result
        assert 'global' in result
        assert 'bind' in result
        assert 'alias' in result
        assert result['alias']['のアレ'] == 'ラベル'

    def test_multi_document_config_in_embedz(self, tmp_path):
        """Test using multi-document config file with embedz block"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""---
global:
  title: "Test Report"
---
global:
  author: "John Doe"
---
""")

        # Use config in embedz block
        code = f"""---
config: {config_file}
---
Title: {{{{ title }}}}, Author: {{{{ author }}}}
"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert result is not None
        result_text = pf.stringify(pf.Doc(*result))
        assert 'Test Report' in result_text
        assert 'John Doe' in result_text
