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
local:
  threshold: 100
  label: "High"
global:
  author: "Arthur"
name: my-template
template: base-template
---
Template content"""

        config, template, data = parse_code_block(text)

        assert config['data'] == 'file.csv'
        assert config['format'] == 'csv'
        assert config['header'] is True
        assert config['local']['threshold'] == 100
        assert config['global']['author'] == 'Arthur'
        assert config['name'] == 'my-template'
        assert config['template'] == 'base-template'
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
