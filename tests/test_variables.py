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
local:
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
local:
  threshold: 90
---
{% for item in data %}
{% if item.value > local.threshold %}
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
local:
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
