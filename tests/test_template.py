"""Tests for template processing"""
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
name: test-template
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
name: list-template
---
{% for row in data %}
- {{ row.name }}
{% endfor %}"""

        elem1 = pf.CodeBlock(save_code, classes=['embedz'])
        doc = pf.Doc()
        process_embedz(elem1, doc)

        # Then use it
        use_code = """---
template: list-template
format: json
---
[{"name": "Arthur"}, {"name": "Ford"}]"""

        elem2 = pf.CodeBlock(use_code, classes=['embedz'])
        result = process_embedz(elem2, doc)

        assert isinstance(result, list)
        assert 'list-template' in SAVED_TEMPLATES

    def test_use_nonexistent_template_fails(self):
        code = """---
template: nonexistent
format: json
---
[{"name": "Arthur"}]"""

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        with pytest.raises(ValueError, match="Template 'nonexistent' not found"):
            process_embedz(elem, doc)


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
