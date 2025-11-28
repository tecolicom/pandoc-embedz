"""Tests for external config files and standalone rendering."""

from pathlib import Path
import panflute as pf


def _reset_state():
    from pandoc_embedz.config import SAVED_TEMPLATES
    import pandoc_embedz.filter as filter_module

    SAVED_TEMPLATES.clear()
    filter_module.GLOBAL_VARS.clear()
    filter_module.CONTROL_STRUCTURES_PARTS.clear()


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
define: helper-macros
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


def test_stdin_data_source():
    """Data can be read from stdin using data: '-'."""
    from pandoc_embedz.main import render_standalone_text
    import sys
    from io import StringIO

    _reset_state()

    # Mock stdin with CSV data
    original_stdin = sys.stdin
    sys.stdin = StringIO("name,value\nApple,10\nBanana,5\n")

    try:
        template = '''---
data: "-"
format: csv
---
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}'''
        result = render_standalone_text(template)
        assert 'Apple: 10' in result
        assert 'Banana: 5' in result
    finally:
        sys.stdin = original_stdin


def test_template_text_option(capsys):
    """Template can be specified via -t option."""
    from pandoc_embedz.main import run_standalone
    import sys
    from io import StringIO

    _reset_state()

    # Mock stdin with lines data
    original_stdin = sys.stdin
    sys.stdin = StringIO("line1\nline2\nline3\n")

    try:
        run_standalone(
            files=[],
            template_text='{% for item in data %}* {{ item }}\n{% endfor %}',
            data_format='lines'
        )
        captured = capsys.readouterr().out
        assert '* line1' in captured
        assert '* line2' in captured
        assert '* line3' in captured
    finally:
        sys.stdin = original_stdin


def test_format_option(capsys):
    """Data format can be specified via -f option."""
    from pandoc_embedz.main import run_standalone
    import sys
    from io import StringIO

    _reset_state()

    # Mock stdin with JSON data
    original_stdin = sys.stdin
    sys.stdin = StringIO('[{"name":"Test","value":42}]')

    try:
        run_standalone(
            files=[],
            template_text='{% for item in data %}{{ item.name }}: {{ item.value }}\n{% endfor %}',
            data_format='json'
        )
        captured = capsys.readouterr().out
        assert 'Test: 42' in captured
    finally:
        sys.stdin = original_stdin


def test_template_and_file_conflict(tmp_path):
    """Cannot specify both -t and template files."""
    from pandoc_embedz.main import main
    import sys

    file = tmp_path / "template.md"
    file.write_text("test", encoding='utf-8')

    # Mock sys.argv
    original_argv = sys.argv
    sys.argv = ['pandoc-embedz', '-s', '-t', 'template text', str(file)]

    try:
        import pytest
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
    finally:
        sys.argv = original_argv


def test_multiple_files_no_stdin_auto_detection(tmp_path):
    """Multiple files should not auto-detect stdin to avoid consuming it on first file."""
    from pandoc_embedz.main import run_standalone
    import sys
    from io import StringIO

    _reset_state()

    # Create two template files without data: specification
    file1 = tmp_path / "template1.md"
    file1.write_text('{% if data %}{{ data[0] }}{% else %}No data 1{% endif %}', encoding='utf-8')

    file2 = tmp_path / "template2.md"
    file2.write_text('{% if data %}{{ data[0] }}{% else %}No data 2{% endif %}', encoding='utf-8')

    # Mock stdin with data
    original_stdin = sys.stdin
    sys.stdin = StringIO("test")

    try:
        from io import StringIO
        import sys as sys_module
        output = StringIO()
        original_stdout = sys_module.stdout
        sys_module.stdout = output

        run_standalone(files=[str(file1), str(file2)])

        sys_module.stdout = original_stdout
        result = output.getvalue()

        # Both files should show "No data" because stdin auto-detection is disabled
        assert 'No data 1' in result
        assert 'No data 2' in result
    finally:
        sys.stdin = original_stdin


def test_template_text_without_format_no_stdin(capsys):
    """Template text without -f option should not read from stdin."""
    from pandoc_embedz.main import run_standalone
    import sys
    from io import StringIO

    _reset_state()

    # Mock stdin with data (should not be consumed)
    original_stdin = sys.stdin
    sys.stdin = StringIO("should not be read")

    try:
        run_standalone(
            files=[],
            template_text='Static text without data'
        )
        captured = capsys.readouterr().out
        assert 'Static text without data' in captured
        assert 'should not be read' not in captured
    finally:
        sys.stdin = original_stdin


def test_template_text_with_format_reads_stdin(capsys):
    """Template text with -f option should read from stdin."""
    from pandoc_embedz.main import run_standalone
    import sys
    from io import StringIO

    _reset_state()

    # Mock stdin with data
    original_stdin = sys.stdin
    sys.stdin = StringIO("line1\nline2")

    try:
        run_standalone(
            files=[],
            template_text='{% for item in data %}{{ item }}\n{% endfor %}',
            data_format='lines'
        )
        captured = capsys.readouterr().out
        assert 'line1' in captured
        assert 'line2' in captured
    finally:
        sys.stdin = original_stdin
