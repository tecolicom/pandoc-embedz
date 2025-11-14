"""Tests for data loading functionality"""
import pytest
from pathlib import Path
from io import StringIO
from pandoc_embedz.filter import load_data, guess_format_from_filename

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class TestGuessFormat:
    """Tests for format auto-detection"""

    def test_csv_extension(self):
        assert guess_format_from_filename('data.csv') == 'csv'

    def test_tsv_extension(self):
        assert guess_format_from_filename('data.tsv') == 'tsv'

    def test_json_extension(self):
        assert guess_format_from_filename('data.json') == 'json'

    def test_yaml_extension(self):
        assert guess_format_from_filename('data.yaml') == 'yaml'
        assert guess_format_from_filename('data.yml') == 'yaml'

    def test_txt_extension(self):
        assert guess_format_from_filename('data.txt') == 'lines'

    def test_default_to_csv(self):
        assert guess_format_from_filename('data.unknown') == 'csv'


class TestLoadCSV:
    """Tests for CSV data loading"""

    def test_load_csv_with_header(self):
        data = load_data(str(FIXTURES_DIR / 'sample.csv'), format='csv', has_header=True)
        assert len(data) == 3
        assert data[0]['name'] == 'Arthur'
        assert data[0]['value'] == 42
        assert data[0]['category'] == 'A'

    def test_load_csv_without_header(self):
        data = load_data(str(FIXTURES_DIR / 'sample.csv'), format='csv', has_header=False)
        assert len(data) == 4  # Including header row as data
        assert isinstance(data[0], list)

    def test_load_csv_inline(self):
        csv_data = StringIO("name,value\nArthur,100\nFord,85")
        data = load_data(csv_data, format='csv', has_header=True)
        assert len(data) == 2
        assert data[0]['name'] == 'Arthur'


class TestLoadTSV:
    """Tests for TSV data loading"""

    def test_load_tsv_with_header(self):
        data = load_data(str(FIXTURES_DIR / 'sample.tsv'), format='tsv', has_header=True)
        assert len(data) == 3
        assert data[0]['name'] == 'Arthur'
        assert data[1]['name'] == 'Ford'

    def test_load_tsv_inline(self):
        tsv_data = StringIO("name\tvalue\nArthur\t42\nFord\t100")
        data = load_data(tsv_data, format='tsv', has_header=True)
        assert len(data) == 2
        assert data[0]['value'] == 42


class TestLoadSSV:
    """Tests for SSV (space-separated) data loading"""

    def test_load_ssv_with_header(self):
        ssv_data = StringIO("name value category\nArthur 42 A\nFord 100 B")
        data = load_data(ssv_data, format='ssv', has_header=True)
        assert len(data) == 2
        assert data[0]['name'] == 'Arthur'
        assert data[0]['value'] == 42

    def test_load_ssv_without_header(self):
        ssv_data = StringIO("Arthur 42 A\nFord 100 B")
        data = load_data(ssv_data, format='ssv', has_header=False)
        assert len(data) == 2
        assert isinstance(data[0], list)
        assert data[0][0] == 'Arthur'

    def test_load_spaces_alias_with_header(self):
        """Test that 'spaces' is an alias for 'ssv' with header"""
        spaces_data = StringIO("name value category\nArthur 42 A\nFord 100 B")
        data = load_data(spaces_data, format='spaces', has_header=True)
        assert len(data) == 2
        assert data[0]['name'] == 'Arthur'
        assert data[0]['value'] == 42

    def test_load_spaces_alias_without_header(self):
        """Test that 'spaces' is an alias for 'ssv' without header"""
        spaces_data = StringIO("Arthur 42 A\nFord 100 B")
        data = load_data(spaces_data, format='spaces', has_header=False)
        assert len(data) == 2
        assert isinstance(data[0], list)
        assert data[0][0] == 'Arthur'


class TestLoadJSON:
    """Tests for JSON data loading"""

    def test_load_json_file(self):
        data = load_data(str(FIXTURES_DIR / 'sample.json'), format='json')
        assert len(data) == 3
        assert data[0]['name'] == 'Arthur'
        assert data[0]['value'] == 42

    def test_load_json_inline(self):
        json_data = StringIO('[{"name": "Arthur", "value": 42}]')
        data = load_data(json_data, format='json')
        assert len(data) == 1
        assert data[0]['name'] == 'Arthur'

    def test_load_json_object(self):
        json_data = StringIO('{"title": "Test", "count": 5}')
        data = load_data(json_data, format='json')
        assert data['title'] == 'Test'
        assert data['count'] == 5


class TestLoadYAML:
    """Tests for YAML data loading"""

    def test_load_yaml_file(self):
        data = load_data(str(FIXTURES_DIR / 'sample.yaml'), format='yaml')
        assert len(data) == 3
        assert data[0]['name'] == 'Arthur'
        assert data[0]['value'] == 42

    def test_load_yaml_inline(self):
        yaml_data = StringIO("- name: Arthur\n  value: 42\n- name: Ford\n  value: 100")
        data = load_data(yaml_data, format='yaml')
        assert len(data) == 2
        assert data[0]['name'] == 'Arthur'


class TestLoadLines:
    """Tests for lines format data loading"""

    def test_load_lines_file(self):
        data = load_data(str(FIXTURES_DIR / 'sample.txt'), format='lines')
        assert len(data) == 3
        assert data[0] == 'Arthur'
        assert data[1] == 'Ford'
        assert data[2] == 'Zaphod'

    def test_load_lines_inline(self):
        lines_data = StringIO("Arthur\nFord\nZaphod\n")
        data = load_data(lines_data, format='lines')
        assert len(data) == 3
        assert data[0] == 'Arthur'

    def test_load_lines_skip_empty(self):
        lines_data = StringIO("Arthur\n\nFord\n\n\nZaphod")
        data = load_data(lines_data, format='lines')
        assert len(data) == 3  # Empty lines removed


class TestAutoDetection:
    """Tests for format auto-detection"""

    def test_csv_auto_detect(self):
        data = load_data(str(FIXTURES_DIR / 'sample.csv'))
        assert len(data) == 3
        assert data[0]['name'] == 'Arthur'

    def test_json_auto_detect(self):
        data = load_data(str(FIXTURES_DIR / 'sample.json'))
        assert len(data) == 3
        assert data[0]['name'] == 'Arthur'

    def test_yaml_auto_detect(self):
        data = load_data(str(FIXTURES_DIR / 'sample.yaml'))
        assert len(data) == 3
        assert data[0]['name'] == 'Arthur'

    def test_txt_auto_detect(self):
        data = load_data(str(FIXTURES_DIR / 'sample.txt'))
        assert len(data) == 3
        assert data[0] == 'Arthur'
