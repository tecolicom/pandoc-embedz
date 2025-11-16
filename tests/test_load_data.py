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

    def test_toml_extension(self):
        assert guess_format_from_filename('data.toml') == 'toml'

    def test_sqlite_extensions(self):
        assert guess_format_from_filename('data.db') == 'sqlite'
        assert guess_format_from_filename('data.sqlite') == 'sqlite'
        assert guess_format_from_filename('data.sqlite3') == 'sqlite'

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

    def test_load_csv_with_query(self):
        """Test CSV with SQL query filter"""
        data = load_data(
            str(FIXTURES_DIR / 'sample.csv'),
            format='csv',
            query='SELECT * FROM data WHERE category = "A"'
        )
        assert len(data) == 2
        assert data[0]['name'] == 'Arthur'
        assert data[1]['name'] == 'Zaphod'

    def test_load_csv_with_aggregation_query(self):
        """Test CSV with SQL aggregation"""
        data = load_data(
            str(FIXTURES_DIR / 'sample.csv'),
            format='csv',
            query='SELECT category, COUNT(*) as count, AVG(value) as avg_value FROM data GROUP BY category'
        )
        assert len(data) == 2
        # Category A has 2 items (Arthur:42, Zaphod:99), avg = 70.5
        # Category B has 1 item (Ford:100), avg = 100
        cat_a = [row for row in data if row['category'] == 'A'][0]
        assert cat_a['count'] == 2
        assert cat_a['avg_value'] == 70.5

    def test_load_csv_with_order_by_query(self):
        """Test CSV with SQL ORDER BY"""
        data = load_data(
            str(FIXTURES_DIR / 'sample.csv'),
            format='csv',
            query='SELECT * FROM data ORDER BY value DESC'
        )
        assert len(data) == 3
        assert data[0]['name'] == 'Ford'  # value = 100
        assert data[1]['name'] == 'Zaphod'  # value = 99
        assert data[2]['name'] == 'Arthur'  # value = 42


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

    def test_load_tsv_with_spaces_in_values(self):
        """Test that TSV correctly handles spaces within field values"""
        tsv_data = StringIO("name\tvalue\tcomment\nArthur Dent\t42\tHoopy frood\nFord Prefect\t100\tGreat guy")
        data = load_data(tsv_data, format='tsv', has_header=True)

        assert len(data) == 2
        # Spaces within values should be preserved
        assert data[0]['name'] == 'Arthur Dent'
        assert data[0]['comment'] == 'Hoopy frood'
        assert data[1]['name'] == 'Ford Prefect'
        assert data[1]['comment'] == 'Great guy'

    def test_load_tsv_without_header(self):
        """Test TSV without header row"""
        tsv_data = StringIO("Arthur Dent\t42\nFord Prefect\t100")
        data = load_data(tsv_data, format='tsv', has_header=False)

        assert len(data) == 2
        assert data[0][0] == 'Arthur Dent'
        assert data[0][1] == 42


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


class TestLoadTOML:
    """Tests for TOML data loading"""

    def test_load_toml_file(self):
        data = load_data(str(FIXTURES_DIR / 'sample.toml'), format='toml')
        assert 'items' in data
        assert len(data['items']) == 3
        assert data['items'][0]['name'] == 'Arthur'
        assert data['items'][0]['value'] == 42

    def test_load_toml_inline(self):
        toml_data = StringIO('[items]\nname = "Arthur"\nvalue = 42\n\n[config]\ntitle = "Test"')
        data = load_data(toml_data, format='toml')
        assert data['items']['name'] == 'Arthur'
        assert data['items']['value'] == 42
        assert data['config']['title'] == 'Test'


class TestLoadSQLite:
    """Tests for SQLite database loading"""

    def test_load_sqlite_with_table(self):
        data = load_data(str(FIXTURES_DIR / 'sample.db'), format='sqlite', table='items')
        assert len(data) == 3
        assert data[0]['name'] == 'Arthur'
        assert data[0]['value'] == 42
        assert data[0]['category'] == 'A'

    def test_load_sqlite_with_query(self):
        data = load_data(
            str(FIXTURES_DIR / 'sample.db'),
            format='sqlite',
            query='SELECT * FROM items WHERE category = "A"'
        )
        assert len(data) == 2
        assert data[0]['name'] == 'Arthur'
        assert data[1]['name'] == 'Zaphod'

    def test_load_sqlite_query_overrides_table(self):
        """When both query and table are specified, query takes precedence"""
        data = load_data(
            str(FIXTURES_DIR / 'sample.db'),
            format='sqlite',
            table='items',
            query='SELECT * FROM metadata'
        )
        assert len(data) == 2
        assert data[0]['key'] == 'author'

    def test_load_sqlite_requires_table_or_query(self):
        """SQLite format requires either table or query parameter"""
        with pytest.raises(ValueError, match="requires either 'table' or 'query'"):
            load_data(str(FIXTURES_DIR / 'sample.db'), format='sqlite')

    def test_load_sqlite_no_inline_support(self):
        """SQLite does not support inline data"""
        with pytest.raises(ValueError, match="does not support inline data"):
            load_data(StringIO("dummy"), format='sqlite', table='items')


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

    def test_toml_auto_detect(self):
        data = load_data(str(FIXTURES_DIR / 'sample.toml'))
        assert 'items' in data
        assert len(data['items']) == 3
        assert data['items'][0]['name'] == 'Arthur'

    def test_sqlite_auto_detect(self):
        """SQLite auto-detects format but still requires table parameter"""
        data = load_data(str(FIXTURES_DIR / 'sample.db'), table='items')
        assert len(data) == 3
        assert data[0]['name'] == 'Arthur'

    def test_txt_auto_detect(self):
        data = load_data(str(FIXTURES_DIR / 'sample.txt'))
        assert len(data) == 3
        assert data[0] == 'Arthur'


class TestMultiTableSQL:
    """Tests for multi-table SQL queries (integration test via process_embedz)"""

    def test_multi_table_join(self):
        """Test joining two CSV files with SQL"""
        from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS
        import panflute as pf

        # Clear state
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

        # Create embedz code block with multi-table data
        code = '''---
data:
  products: tests/fixtures/products.csv
  sales: tests/fixtures/sales.csv
query: |
  SELECT
    p.product_name,
    s.quantity,
    s.date
  FROM sales s
  JOIN products p ON s.product_id = p.product_id
  ORDER BY s.date
---
{% for row in data %}
- {{ row.product_name }}: {{ row.quantity }} units on {{ row.date }}
{% endfor %}'''

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        result = process_embedz(elem, doc)

        # Convert result to markdown
        if isinstance(result, list):
            markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
        else:
            markdown = pf.convert_text([result], input_format='panflute', output_format='markdown')

        # Verify output contains joined data
        assert 'Widget' in markdown
        assert 'Gadget' in markdown
        assert 'Doohickey' in markdown
        assert '5 units' in markdown
        assert '2024-01-15' in markdown

    def test_multi_table_aggregation(self):
        """Test aggregating data from multiple tables"""
        from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS
        import panflute as pf

        # Clear state
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

        # Create embedz code block with aggregation
        code = '''---
data:
  products: tests/fixtures/products.csv
  sales: tests/fixtures/sales.csv
query: |
  SELECT
    p.product_name,
    SUM(s.quantity) as total_quantity,
    SUM(s.quantity * p.price) as total_revenue
  FROM sales s
  JOIN products p ON s.product_id = p.product_id
  GROUP BY p.product_name
  ORDER BY total_revenue DESC
---
| Product | Quantity | Revenue |
|---------|----------|---------|
{% for row in data -%}
| {{ row.product_name }} | {{ row.total_quantity }} | ${{ "%.2f" | format(row.total_revenue) }} |
{% endfor -%}'''

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        result = process_embedz(elem, doc)

        # Convert result to markdown
        if isinstance(result, list):
            markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
        else:
            markdown = pf.convert_text([result], input_format='panflute', output_format='markdown')

        # Verify output contains aggregated data
        assert 'Widget' in markdown
        assert 'Gadget' in markdown
        assert 'Doohickey' in markdown

    def test_multi_table_without_query(self):
        """Multi-table data without query allows direct access via data.table_name"""
        from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS
        import panflute as pf

        # Clear state
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

        # Create embedz code block without query - accessing via data.table_name
        code = '''---
data:
  products: tests/fixtures/products.csv
  sales: tests/fixtures/sales.csv
---
## Products
{% for p in data.products %}
- {{ p.product_name }}: ¥{{ p.price }}
{% endfor %}

## Sales
{% for s in data.sales %}
- Sale #{{ s.sale_id }}: {{ s.quantity }} units
{% endfor %}'''

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        result = process_embedz(elem, doc)

        # Convert result to markdown
        if isinstance(result, list):
            markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
        else:
            markdown = pf.convert_text([result], input_format='panflute', output_format='markdown')

        # Verify output contains data from both files
        assert 'Products' in markdown
        assert 'Sales' in markdown
        assert 'Widget' in markdown
        assert 'Gadget' in markdown
        assert 'Sale #101' in markdown
        assert 'Sale #102' in markdown

    def test_multi_table_mixed_formats(self):
        """Multi-table can combine different formats (YAML + CSV)"""
        from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS
        import panflute as pf

        # Clear state
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

        # Create embedz code block combining YAML config and CSV data
        code = '''---
data:
  config: tests/fixtures/config.yaml
  sales: tests/fixtures/sales.csv
---
# {{ data.config.title }}
## {{ data.config.subtitle }}

By {{ data.config.author }} (v{{ data.config.version }})

{% for sale in data.sales[:3] %}
- Sale #{{ sale.sale_id }}: {{ sale.quantity }} units
{% endfor %}'''

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        result = process_embedz(elem, doc)

        # Convert result to markdown
        if isinstance(result, list):
            markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
        else:
            markdown = pf.convert_text([result], input_format='panflute', output_format='markdown')

        # Verify output contains both config and data
        assert '2024 Sales Report' in markdown
        assert 'Q1 Results' in markdown
        assert 'John Doe' in markdown
        assert 'v1.0' in markdown
        assert 'Sale #101' in markdown

    def test_multi_table_inline_csv(self):
        """Multi-table with inline CSV data"""
        from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS
        import panflute as pf

        # Clear state
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

        # Create embedz code block with inline CSV data
        code = '''---
data:
  products: |
    product_id,product_name,price
    1,Widget,1280
    2,Gadget,2480
  sales: |
    sale_id,product_id,quantity
    101,1,5
    102,2,3
---
## Products
{% for p in data.products %}
- {{ p.product_name }}: ¥{{ "{:,}".format(p.price|int) }}
{% endfor %}

## Sales
{% for s in data.sales %}
- Sale #{{ s.sale_id }}: {{ s.quantity }} units
{% endfor %}'''

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        result = process_embedz(elem, doc)

        # Convert result to markdown
        if isinstance(result, list):
            markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
        else:
            markdown = pf.convert_text([result], input_format='panflute', output_format='markdown')

        # Verify output contains data from inline sources
        assert 'Products' in markdown
        assert 'Widget: ¥1,280' in markdown
        assert 'Gadget: ¥2,480' in markdown
        assert 'Sale #101: 5 units' in markdown
        assert 'Sale #102: 3 units' in markdown

    def test_multi_table_inline_yaml(self):
        """Multi-table with inline YAML config and CSV data"""
        from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS
        import panflute as pf

        # Clear state
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

        # Create embedz code block with mixed inline data
        code = '''---
data:
  config:
    format: yaml
    data: |
      title: "Test Report"
      year: 2024
  sales: |
    date,amount
    2024-01-01,100
    2024-01-02,200
---
# {{ data.config.title }} ({{ data.config.year }})

{% for s in data.sales %}
- {{ s.date }}: ${{ s.amount }}
{% endfor %}'''

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        result = process_embedz(elem, doc)

        # Convert result to markdown
        if isinstance(result, list):
            markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
        else:
            markdown = pf.convert_text([result], input_format='panflute', output_format='markdown')

        # Verify output contains both config and data
        assert 'Test Report (2024)' in markdown
        assert '2024-01-01: \\$100' in markdown or '2024-01-01: $100' in markdown
        assert '2024-01-02: \\$200' in markdown or '2024-01-02: $200' in markdown

    def test_multi_table_mixed_inline_and_file(self):
        """Multi-table with both inline data and file paths"""
        from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS
        import panflute as pf

        # Clear state
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

        # Create embedz code block mixing inline and file data
        code = '''---
data:
  config:
    format: yaml
    data: |
      title: "Mixed Source Report"
  products: tests/fixtures/products.csv
  sales: |
    sale_id,product_id,quantity
    999,1,10
---
# {{ data.config.title }}

## Products from file
{% for p in data.products[:2] %}
- {{ p.product_name }}
{% endfor %}

## Sales from inline
{% for s in data.sales %}
- Sale #{{ s.sale_id }}: {{ s.quantity }} units
{% endfor %}'''

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        result = process_embedz(elem, doc)

        # Convert result to markdown
        if isinstance(result, list):
            markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
        else:
            markdown = pf.convert_text([result], input_format='panflute', output_format='markdown')

        # Verify output contains data from both sources
        assert 'Mixed Source Report' in markdown
        assert 'Widget' in markdown  # From file
        assert 'Sale #999: 10 units' in markdown  # From inline

    def test_data_file_and_data_part_mutually_exclusive(self):
        """Error should be raised if both data attribute and inline data are specified"""
        from pandoc_embedz.filter import process_embedz, SAVED_TEMPLATES, GLOBAL_VARS
        import panflute as pf

        # Clear state
        SAVED_TEMPLATES.clear()
        GLOBAL_VARS.clear()

        # Create embedz code block with both data attribute and inline data
        code = '''---
data: tests/fixtures/products.csv
---
{% for p in data %}
- {{ p.product_name }}
{% endfor %}
---
product_id,product_name,price
1,Widget,1280
2,Gadget,2480'''

        elem = pf.CodeBlock(code, classes=['embedz'])
        doc = pf.Doc()

        # Should raise ValueError
        import pytest
        with pytest.raises(ValueError, match="Cannot specify both 'data' attribute and inline data"):
            process_embedz(elem, doc)
