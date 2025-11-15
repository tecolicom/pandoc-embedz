"""Tests for code block parsing"""
import pytest
from pandoc_embedz.filter import parse_code_block


class TestParseCodeBlock:
    """Tests for parse_code_block function"""

    def test_parse_no_yaml_header(self):
        text = """{% for item in data %}
- {{ item }}
{% endfor %}"""

        config, template, data = parse_code_block(text)

        assert config == {}
        assert template == text
        assert data is None

    def test_parse_yaml_only(self):
        text = """---
data: file.csv
format: csv
---"""

        config, template, data = parse_code_block(text)

        assert config['data'] == 'file.csv'
        assert config['format'] == 'csv'
        assert template == ''
        assert data is None

    def test_parse_yaml_and_template(self):
        text = """---
data: file.csv
---
{% for row in data %}
- {{ row.name }}
{% endfor %}"""

        config, template, data = parse_code_block(text)

        assert config['data'] == 'file.csv'
        assert '{% for row in data %}' in template
        assert data is None

    def test_parse_yaml_template_and_data(self):
        text = """---
format: csv
---
{% for row in data %}
- {{ row.name }}
{% endfor %}
---
name,value
Arthur,100
Ford,85"""

        config, template, data = parse_code_block(text)

        assert config['format'] == 'csv'
        assert '{% for row in data %}' in template
        assert 'name,value' in data
        assert 'Arthur,100' in data

    def test_parse_empty_yaml_header(self):
        text = """---
---
Template here"""

        config, template, data = parse_code_block(text)

        assert config == {}
        assert template == 'Template here'
        assert data is None

    def test_parse_complex_yaml_config(self):
        text = """---
data: file.csv
format: csv
header: true
with:
  threshold: 100
  label: "High"
global:
  author: "Arthur"
name: my-template
as: base-template
---
Template content"""

        config, template, data = parse_code_block(text)

        assert config['data'] == 'file.csv'
        assert config['format'] == 'csv'
        assert config['header'] is True
        assert config['with']['threshold'] == 100
        assert config['global']['author'] == 'Arthur'
        assert config['name'] == 'my-template'
        assert config['as'] == 'base-template'
        assert template == 'Template content'

    def test_parse_multiline_template(self):
        text = """---
format: json
---
# Title

{% for item in data %}
## {{ item.name }}

Content here.
{% endfor %}

# Conclusion"""

        config, template, data = parse_code_block(text)

        assert config['format'] == 'json'
        assert '# Title' in template
        assert '# Conclusion' in template

    def test_parse_inline_json_data(self):
        text = """---
format: json
---
Template
---
[
  {"name": "Arthur", "value": 100},
  {"name": "Ford", "value": 85}
]"""

        config, template, data = parse_code_block(text)

        assert config['format'] == 'json'
        assert template == 'Template'
        assert '"name": "Arthur"' in data
        assert '"value": 100' in data

    def test_parse_preserves_leading_whitespace(self):
        """Leading whitespace should be preserved (unlike .strip())"""
        text = """---
name: test
---
    indented content
    more indented"""

        config, template, data = parse_code_block(text)

        assert template == '    indented content\n    more indented'
        assert template.startswith('    ')  # Leading whitespace preserved

    def test_parse_removes_trailing_newlines(self):
        """Trailing newlines should be removed (like shell $(...))"""
        text = """---
name: test
---
content


"""

        config, template, data = parse_code_block(text)

        assert template == 'content'  # Trailing newlines removed
        assert not template.endswith('\n')

    def test_parse_preserves_internal_newlines(self):
        """Internal newlines should be preserved"""
        text = """---
name: test
---
line1

line2

line3"""

        config, template, data = parse_code_block(text)

        assert template == 'line1\n\nline2\n\nline3'
        assert template.count('\n') == 4  # 2 blank lines = 4 newlines total
