"""Tests for template processing"""
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


class TestBasicTemplating:
    """Tests for basic template rendering"""

    def test_simple_template_inline_csv(self):
        code = """---
format: csv
---
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
---
name,value
Arthur,100
Ford,85"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        # Result should be a list of elements
        assert isinstance(result, list)
        assert len(result) > 0

    def test_template_with_conditionals(self):
        code = """---
format: json
---
{% for item in data %}
{% if item.value > 90 %}
- High: {{ item.name }}
{% endif %}
{% endfor %}
---
[{"name": "Arthur", "value": 100}, {"name": "Ford", "value": 85}]"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)

    def test_template_with_filters(self):
        code = """---
format: json
---
{{ data | length }} items
---
[{"name": "Arthur"}, {"name": "Ford"}, {"name": "Charlie"}]"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)


class TestTemplateReuse:
    """Tests for template name/reuse functionality"""

    def test_save_template(self):
        code = """---
define: test-template
---
{% for row in data %}
- {{ row.name }}
{% endfor %}"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        # Template should be saved but no output (no data)
        assert result == []
        assert 'test-template' in SAVED_TEMPLATES

    def test_use_saved_template(self):
        # First, save a template
        save_code = """---
define: list-template
---
{% for row in data %}
- {{ row.name }}
{% endfor %}"""

        elem1 = pf.CodeBlock(save_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Then use it with 3 separators: YAML header → empty template → data
        use_code = """---
as: list-template
format: json
---

---
[{"name": "Arthur"}, {"name": "Ford"}]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        # Verify result type and content
        assert isinstance(result, list)
        assert 'list-template' in SAVED_TEMPLATES

        # Verify rendered content
        markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert 'Arthur' in markdown
        assert 'Ford' in markdown

    def test_use_nonexistent_template_fails(self):
        # Template usage with inline data requires 3 separators
        code = """---
as: nonexistent
format: json
---

---
[{"name": "Arthur"}]"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        with pytest.raises(ValueError, match="Template 'nonexistent' not found"):
            process_embedz(elem, doc)


class TestRenderWithoutData:
    """Ensure templates without explicit data still render when needed."""

    def test_embedz_block_renders_without_data(self):
        code = """---
with:
  title: Example
---
# {{ title }}
"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
        assert '# Example' in markdown

    def test_named_template_without_data_is_definition_only(self):
        code = """---
define: macros
---
{% macro HELLO(name) %}Hello {{ name }}{% endmacro %}
"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert result == []


class TestStructuredData:
    """Tests for nested JSON/YAML structures"""

    def test_nested_json_structure(self):
        code = """---
format: json
---
# {{ data.title }}
{% for section in data.sections %}
## {{ section.name }}
{% endfor %}
---
{
  "title": "Report",
  "sections": [
    {"name": "Introduction"},
    {"name": "Conclusion"}
  ]
}"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)


class TestTemplateInclude:
    """Tests for template inclusion ({% include %}) functionality"""

    def test_basic_include(self):
        # First, define a template
        define_code = """---
define: item-format
---
- {{ item.name }}: {{ item.value }}"""

        elem1 = pf.CodeBlock(define_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Then use it with {% include %}
        use_code = """---
format: json
---
{% for item in data %}
{% include 'item-format' with context %}
{% endfor %}
---
[{"name": "Arthur", "value": 100}, {"name": "Ford", "value": 85}]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_nested_include(self):
        # Define multiple templates
        define_date = """---
define: date-format
---
{{ item.date }}"""

        define_title = """---
define: title-format
---
**{{ item.title }}**"""

        define_entry = """---
define: jvn-entry
---
- {% include 'date-format' with context %} {% include 'title-format' with context %}"""

        doc = pf.Doc()
        process_embedz(pf.CodeBlock(define_date, classes=['embedz']), doc)
        process_embedz(pf.CodeBlock(define_title, classes=['embedz']), doc)
        process_embedz(pf.CodeBlock(define_entry, classes=['embedz']), doc)

        # Use the composite template
        use_code = """---
format: json
---
{% for item in data %}
{% include 'jvn-entry' with context %}
{% endfor %}
---
[{"date": "2024-01-15", "title": "Apache HTTP Server vulnerability"}]"""

        elem = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem, doc)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_include_with_conditionals(self):
        # Define a template with conditionals
        define_code = """---
name: severity-badge
---
{% if item.severity == "high" %}🔴{% elif item.severity == "medium" %}🟡{% else %}🟢{% endif %}"""

        elem1 = pf.CodeBlock(define_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use it
        use_code = """---
format: json
---
{% for item in data %}
- {% include 'severity-badge' with context %} {{ item.title }}
{% endfor %}
---
[{"title": "Critical bug", "severity": "high"}, {"title": "Minor issue", "severity": "low"}]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        assert len(result) > 0


class TestTemplateMacros:
    """Tests for Jinja2 macro functionality"""

    def test_basic_macro(self):
        # Define a macro
        define_code = """---
name: formatters
---
{% macro bold(text) -%}
**{{ text }}**
{%- endmacro %}"""

        elem1 = pf.CodeBlock(define_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use the macro
        use_code = """---
format: json
---
{% from 'formatters' import bold %}
{% for item in data %}
- {{ bold(item) }}
{% endfor %}
---
["Apple", "Banana"]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_macro_with_multiple_parameters(self):
        # Define macro with multiple parameters
        define_code = """---
name: multi-param
---
{% macro format_item(name, value, prefix="Item: ") -%}
{{ prefix }}{{ name }} = {{ value }}
{%- endmacro %}"""

        elem1 = pf.CodeBlock(define_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use with different parameters
        use_code = """---
format: json
---
{% from 'multi-param' import format_item %}
{% for item in data %}
- {{ format_item(item.name, item.count, "Total: ") }}
{% endfor %}
---
[{"name": "A", "count": 10}, {"name": "B", "count": 20}]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_macro_with_conditionals(self):
        # Define conditional macro
        define_code = """---
name: conditional-macro
---
{% macro severity_badge(level) -%}
{% if level == "high" %}🔴{% elif level == "medium" %}🟡{% else %}🟢{% endif %}
{%- endmacro %}"""

        elem1 = pf.CodeBlock(define_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use the macro
        use_code = """---
format: json
---
{% from 'conditional-macro' import severity_badge %}
{% for item in data %}
- {{ severity_badge(item.level) }} {{ item.title }}
{% endfor %}
---
[{"title": "Critical", "level": "high"}, {"title": "Minor", "level": "low"}]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_nested_macros(self):
        # Define macros that call each other
        define_code = """---
name: nested-macros
---
{% macro inner(text) -%}
**{{ text }}**
{%- endmacro %}

{% macro outer(text) -%}
[ {{ inner(text) }} ]
{%- endmacro %}"""

        elem1 = pf.CodeBlock(define_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Use the outer macro
        use_code = """---
format: json
---
{% from 'nested-macros' import outer %}
{% for item in data %}
- {{ outer(item) }}
{% endfor %}
---
["Test"]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        assert len(result) > 0


class TestCodeBlockClassDetection:
    """Tests for code block class detection"""

    def test_embedz_class_recognized(self):
        code = """---
format: json
---
Test
---
[{"name": "Arthur"}]"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert isinstance(result, list)

    def test_non_embedz_class_ignored(self):
        code = "Some code"
        elem = pf.CodeBlock(code, classes=['python'])
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        # Should return the element unchanged
        assert result == elem

    def test_no_class_ignored(self):
        code = "Some code"
        elem = pf.CodeBlock(code)
        doc = pf.Doc()
        result = process_embedz(elem, doc)

        assert result == elem
