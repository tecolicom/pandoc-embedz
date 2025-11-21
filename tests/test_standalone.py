"""Tests for external config files and standalone rendering."""

from pathlib import Path
import panflute as pf


def _reset_state():
    from pandoc_embedz.config import SAVED_TEMPLATES
    import pandoc_embedz.filter as filter_module

    SAVED_TEMPLATES.clear()
    filter_module.GLOBAL_VARS.clear()
    filter_module.CONTROL_STRUCTURES_STR = ""


def test_config_file_merged_in_code_block():
    """Code blocks can load external YAML config files."""
    from pandoc_embedz.filter import process_embedz

    _reset_state()
    code = '''---
config: tests/fixtures/embedz_config.yaml
---
# {{ global.title }}
{% for row in data %}
- {{ row.name }} ({{ row.category }})
{% endfor %}'''

    elem = pf.CodeBlock(code, classes=['embedz'])
    doc = pf.Doc()
    result = process_embedz(elem, doc)

    if isinstance(result, list):
        markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
    else:
        markdown = pf.convert_text([result], input_format='panflute', output_format='markdown')

    assert 'Sample Report' in markdown
    assert 'Arthur (A)' in markdown
    assert 'Ford (B)' in markdown


def test_config_list_precedence():
    """Later config files override earlier ones."""
    from pandoc_embedz.filter import process_embedz

    _reset_state()
    code = '''---
config:
  - tests/fixtures/embedz_config.yaml
  - tests/fixtures/embedz_override.yaml
---
- {{ global.title }}
- {{ with.prefix }}
'''

    elem = pf.CodeBlock(code, classes=['embedz'])
    doc = pf.Doc()
    result = process_embedz(elem, doc)

    if isinstance(result, list):
        markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
    else:
        markdown = pf.convert_text([result], input_format='panflute', output_format='markdown')

    assert 'Override Title' in markdown
    assert 'Score' in markdown


def test_render_standalone_with_cli_config():
    """Standalone rendering accepts config files via overrides."""
    from pandoc_embedz.filter import render_standalone_text

    _reset_state()
    template = Path('tests/fixtures/cli_template.tex').read_text(encoding='utf-8')
    result = render_standalone_text(
        template,
        {'config': 'tests/fixtures/embedz_config.yaml'}
    )

    assert 'Sample Report' in result
    assert '- Arthur: 42' in result


def test_standalone_preserves_literal_delimiters():
    """Standalone templates treat everything after front matter as template text."""
    from pandoc_embedz.filter import render_standalone_text

    _reset_state()
    template = '''---
config: tests/fixtures/embedz_config.yaml
---
Top line
---
{% for row in data[:1] %}
- {{ row.name }}
{% endfor %}
'''
    result = render_standalone_text(template)
    assert 'Top line' in result
    assert '\n---\n' in result
    assert '- Arthur' in result


def test_standalone_does_not_accept_inline_data_payload():
    """Standalone mode ignores inline data sections; data must come from config."""
    from pandoc_embedz.filter import render_standalone_text

    _reset_state()
    template = '''---
format: csv
---
{% for row in data %}
- {{ row.name }}
{% endfor %}
---
name,value
Foo,1
'''
    result = render_standalone_text(template)
    assert result.strip() == ''
