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
    from pandoc_embedz.main import render_standalone_text

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
    from pandoc_embedz.main import render_standalone_text

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
    from pandoc_embedz.main import render_standalone_text

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
    assert 'name,value' in result
    assert 'Foo,1' in result


def test_standalone_without_data_renders_template():
    """Standalone template without data should render as-is."""
    from pandoc_embedz.main import render_standalone_text

    _reset_state()
    template = '''---
global:
  title: Standalone
---
{{ global.title }}
'''
    result = render_standalone_text(template)
    assert result.strip() == 'Standalone'


def test_standalone_preserves_trailing_newlines():
    """Standalone fallback keeps original trailing newlines."""
    from pandoc_embedz.main import render_standalone_text

    _reset_state()
    template = '''---
---
Line

'''
    result = render_standalone_text(template)
    assert result.endswith('Line\n\n')


def test_standalone_appends_newline_when_missing():
    """Standalone fallback adds a single newline if none existed."""
    from pandoc_embedz.main import render_standalone_text

    _reset_state()
    template = '''---
---
Line'''
    result = render_standalone_text(template)
    assert result.endswith('Line\n')

def test_run_standalone_multiple_files(tmp_path, capsys):
    """Multiple files are rendered in order; definition-only files emit nothing."""
    from pandoc_embedz.main import run_standalone

    file1 = tmp_path / "file1.md"
    file1.write_text(
        """---
data: tests/fixtures/sample.csv
---
{% for row in data[:1] %}
{{ row.name }}
{% endfor %}
""",
        encoding='utf-8'
    )

    file2 = tmp_path / "file2.md"
    file2.write_text(
        """---
with:
  title: Standalone
---
Title: {{ title }}
""",
        encoding='utf-8'
    )

    file3 = tmp_path / "defs.md"
    file3.write_text(
        """---
name: helper-macros
---
{% macro HELLO(name) %}Hello {{ name }}{% endmacro %}
""",
        encoding='utf-8'
    )

    run_standalone([str(file1), str(file2), str(file3)])

    captured = capsys.readouterr().out
    assert 'Arthur' in captured
    assert 'Title: Standalone' in captured
    assert 'HELLO' not in captured
