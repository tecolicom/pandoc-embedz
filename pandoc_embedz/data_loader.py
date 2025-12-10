"""Data loading module for pandoc-embedz

Handles loading data from various formats using a dispatch table pattern.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from functools import partial
import pandas as pd
import yaml
import json
import sqlite3
import sys
from io import StringIO
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    from sqlite_utils import Database as SqliteUtilsDatabase
except ImportError:
    SqliteUtilsDatabase = None

# ─────────────────────────────────────────────────────────────────────────────
# Constants

FORMAT_EXTENSIONS = {
    '.txt': 'lines',
    '.tsv': 'tsv',
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.db': 'sqlite',
    '.sqlite': 'sqlite',
    '.sqlite3': 'sqlite',
}

DEFAULT_FORMAT = 'csv'

# Separator mapping for tabular formats
SEP_MAP = {
    'tsv': '\t',
    'ssv': r'\s+',
    'spaces': r'\s+',
    'csv': ',',
}

# ─────────────────────────────────────────────────────────────────────────────
# SQL Query Support

def _apply_sql_query(df: pd.DataFrame, query: str, table_name: str = 'data') -> List[Dict[str, Any]]:
    """Apply SQL query to DataFrame using in-memory SQLite"""
    return _apply_sql_query_multi({table_name: df}, query)

def _apply_sql_query_multi(tables: Dict[str, pd.DataFrame], query: str) -> List[Dict[str, Any]]:
    """Apply SQL query to multiple DataFrames using in-memory SQLite"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row

    try:
        for table_name, df in tables.items():
            df.to_sql(table_name, conn, index=False, if_exists='replace')

        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────────
# Format Loaders

def _build_csv_read_kwargs(sep: str, has_header: Optional[bool] = None) -> Dict[str, Any]:
    r"""Build pandas read_csv kwargs for the given separator.

    Args:
        sep: Separator string (e.g., ',', '\t', r'\s+')
        has_header: If provided, sets the 'header' parameter

    Returns:
        Dict of kwargs for pd.read_csv()
    """
    kwargs: Dict[str, Any] = {}

    if sep is not None:
        kwargs['sep'] = sep

    if has_header is not None:
        kwargs['header'] = 0 if has_header else None

    if sep == r'\s+':
        kwargs['engine'] = 'python'

    return kwargs

def _read_source(source: Union[str, StringIO]) -> str:
    """Read content from file path or StringIO.

    Args:
        source: File path string or StringIO object

    Returns:
        Content as string
    """
    return source.getvalue() if isinstance(source, StringIO) else Path(source).read_text(encoding='utf-8')

def _load_json(source: Union[str, StringIO], **kwargs) -> Union[List[Any], Dict[str, Any]]:
    """Load JSON format

    Returns empty list for empty input instead of raising an error.
    """
    content = _read_source(source)

    # Handle empty input - return empty list
    if not content.strip():
        return []

    return json.loads(content)

def _load_yaml(source: Union[str, StringIO], **kwargs) -> Union[List[Any], Dict[str, Any]]:
    """Load YAML format"""
    content = _read_source(source)
    return yaml.safe_load(content)

def _load_toml(source: Union[str, StringIO], **kwargs) -> Dict[str, Any]:
    """Load TOML format"""
    if tomllib is None:
        raise ImportError(
            "TOML support requires 'tomli' package for Python < 3.11. "
            "Install with: pip install tomli"
        )
    content = _read_source(source)
    return tomllib.loads(content)

def _quote_identifier(name: str) -> str:
    """Quote SQLite identifier (table/column name) to prevent SQL injection.

    Uses double-quote escaping per SQL standard (supported by SQLite).
    Any double quotes in the name are escaped by doubling them.

    Args:
        name: Identifier name to quote

    Returns:
        str: Safely quoted identifier

    Examples:
        >>> _quote_identifier('items')
        '"items"'
        >>> _quote_identifier('my table')
        '"my table"'
        >>> _quote_identifier('test"quote')
        '"test""quote"'
    """
    return '"' + name.replace('"', '""') + '"'


def _load_sqlite(source: Union[str, StringIO], **kwargs) -> List[Dict[str, Any]]:
    """Load SQLite database

    Uses sqlite-utils if available for improved API, falls back to sqlite3.
    """
    if isinstance(source, StringIO):
        raise ValueError(
            "SQLite format does not support inline data. "
            "Use an external .db/.sqlite/.sqlite3 file."
        )

    query = kwargs.get('query')
    table = kwargs.get('table')

    if not query and not table:
        raise ValueError("SQLite format requires either 'table' or 'query' parameter")

    # Use sqlite-utils if available (cleaner API)
    if SqliteUtilsDatabase is not None:
        db = SqliteUtilsDatabase(source)
        if query:
            # Execute query and convert to dicts using column names
            cursor = db.execute(query)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            return list(db[table].rows)

    # Fallback to standard sqlite3
    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()
        if query:
            cursor.execute(query)
        else:
            # Quote table name to prevent SQL injection
            cursor.execute(f"SELECT * FROM {_quote_identifier(table)}")

        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def _load_lines(source: Union[str, StringIO], **kwargs) -> List[str]:
    """Load plain text lines

    Returns each line as a string. Empty lines are preserved as empty strings.
    """
    content = _read_source(source)
    return content.splitlines()

def _load_ssv_with_columns(
    source: Union[str, StringIO],
    columns: int,
    has_header: bool = True,
    **kwargs
) -> Union[List[Dict[str, Any]], List[List[Any]]]:
    """Load SSV format with fixed column count.

    Uses str.split(maxsplit=columns-1) to preserve spaces in the last column.

    Args:
        source: File path or StringIO object
        columns: Number of columns (last column gets all remaining content)
        has_header: Whether first line is header
        **kwargs: Additional options (e.g., query)

    Returns:
        List of dicts (with header) or list of lists (without header)
    """
    content = _read_source(source)
    lines = content.splitlines()

    if not lines:
        return []

    maxsplit = columns - 1
    result: List[List[str]] = []
    header: Optional[List[str]] = None

    for line in lines:
        if not line.strip():
            continue

        parts = line.split(maxsplit=maxsplit)

        # Pad with empty strings if fewer columns than expected
        while len(parts) < columns:
            parts.append('')

        if has_header and header is None:
            header = parts
        else:
            result.append(parts)

    if has_header and header is not None:
        records = [dict(zip(header, row)) for row in result]
        if 'query' in kwargs:
            df = pd.DataFrame(records)
            return _apply_sql_query(df, kwargs['query'])
        return records
    else:
        return result


def _load_csv(
    source: Union[str, StringIO],
    sep: str = ',',
    has_header: bool = True,
    **kwargs
) -> Union[List[Dict[str, Any]], List[List[Any]]]:
    """Load CSV/TSV/SSV format with optional SQL query support

    Returns empty list for empty input instead of raising an error.
    """
    # For SSV with columns parameter, use special handler
    if sep == r'\s+' and 'columns' in kwargs:
        columns = kwargs['columns']
        rest_kwargs = {k: v for k, v in kwargs.items() if k != 'columns'}
        return _load_ssv_with_columns(source, columns, has_header, **rest_kwargs)

    read_kwargs = _build_csv_read_kwargs(sep)

    try:
        if has_header:
            df = pd.read_csv(source, **read_kwargs)
            if 'query' in kwargs:
                return _apply_sql_query(df, kwargs['query'])
            return df.to_dict('records')
        else:
            df = pd.read_csv(source, header=None, **read_kwargs)
            return df.values.tolist()
    except pd.errors.EmptyDataError:
        # pandas raises EmptyDataError for empty or whitespace-only input
        return []

# ─────────────────────────────────────────────────────────────────────────────
# Loader Dispatch Table

LOADERS = {
    'json': _load_json,
    'yaml': _load_yaml,
    'toml': _load_toml,
    'sqlite': _load_sqlite,
    'lines': _load_lines,
    'tsv': partial(_load_csv, sep='\t'),
    'ssv': partial(_load_csv, sep=r'\s+'),
    'csv': _load_csv,
}

# ─────────────────────────────────────────────────────────────────────────────
# Public API

def guess_format_from_filename(filename: str) -> str:
    """Guess data format from filename extension"""
    return FORMAT_EXTENSIONS.get(Path(filename).suffix.lower(), DEFAULT_FORMAT)

def _normalize_data_source(
    value: Union[str, Dict[str, Any]],
    table_name: str,
    data_format: Optional[str] = None,
    validate_path: bool = False
) -> Tuple[Union[str, StringIO], str]:
    """Normalize data source specification to (source, format) tuple"""
    from .config import validate_file_path

    if isinstance(value, dict):
        if 'data' not in value:
            raise ValueError(
                f"Inline data dict for table '{table_name}' must have 'data' key"
            )
        return StringIO(value['data']), value.get('format', DEFAULT_FORMAT)
    elif isinstance(value, str) and '\n' in value:
        return StringIO(value), DEFAULT_FORMAT
    else:
        file_format = data_format or guess_format_from_filename(value)
        source = validate_file_path(value) if validate_path else value
        return source, file_format

def load_data(
    source: Union[str, StringIO],
    format: Optional[str] = None,
    has_header: bool = True,
    **kwargs: Any
) -> Union[List[Any], Dict[str, Any]]:
    """Load data from file or StringIO

    Uses a dispatch table to delegate to format-specific loaders.

    Args:
        source: File path, StringIO object, or '-' for stdin
        format: Data format (csv, tsv, ssv, json, yaml, toml, sqlite, lines)
               If None, auto-detect from filename
        has_header: Whether CSV/TSV/SSV has header row
        **kwargs: Format-specific options (e.g., table/query for sqlite)

    Returns:
        Loaded data (list or dict depending on format)
    """
    from .config import validate_file_path

    # Handle stdin
    if isinstance(source, str) and source == '-':
        source = StringIO(sys.stdin.read())
    elif isinstance(source, str):
        source = validate_file_path(source)

    # Normalize format aliases
    if format == 'spaces':
        format = 'ssv'

    # Auto-detect format
    if format is None:
        format = guess_format_from_filename(source) if isinstance(source, str) else DEFAULT_FORMAT

    # Dispatch to appropriate loader
    loader = LOADERS.get(format, LOADERS[DEFAULT_FORMAT])
    return loader(source, has_header=has_header, **kwargs)

# ─────────────────────────────────────────────────────────────────────────────
# Multi-table Support

def _query_tables(
    data_file: Dict[str, Any],
    data_format: Optional[str],
    has_header: bool,
    query: str
) -> List[Dict[str, Any]]:
    """Load multiple tables and execute SQL query"""
    tables = {}
    for table_name, value in data_file.items():
        source, file_format = _normalize_data_source(
            value, table_name, data_format, validate_path=True
        )

        if file_format not in SEP_MAP:
            raise ValueError(
                f"Multi-table SQL queries only support CSV, TSV, and SSV formats. "
                f"Got '{file_format}' for table '{table_name}'"
            )

        # Load into DataFrame using separator mapping
        sep = SEP_MAP[file_format]
        read_kwargs = _build_csv_read_kwargs(sep, has_header)

        tables[table_name] = pd.read_csv(source, **read_kwargs)

    return _apply_sql_query_multi(tables, query)

def _load_tables(
    data_file: Dict[str, Any],
    data_format: Optional[str],
    has_header: bool,
    load_kwargs: Dict[str, Any]
) -> Dict[str, Any]:
    """Load multiple tables for direct access"""
    datasets = {}
    for table_name, value in data_file.items():
        source, file_format = _normalize_data_source(
            value, table_name, data_format, validate_path=False
        )
        datasets[table_name] = load_data(
            source,
            format=file_format,
            has_header=has_header,
            **load_kwargs
        )
    return datasets

def _load_embedz_data(
    data_file: Optional[Union[str, Dict[str, Any]]],
    data_part: Optional[str],
    config: Dict[str, Any],
    data_format: Optional[str],
    has_header: bool,
    load_kwargs: Dict[str, Any]
) -> Union[List[Any], Dict[str, Any]]:
    """Load data from file(s), inline data, or multi-table sources"""
    if data_file and data_part:
        raise ValueError(
            "Cannot specify both 'data' attribute and inline data. "
            "Use either 'data: filename.csv' or provide inline data after '---', not both."
        )

    if data_file:
        if isinstance(data_file, dict):
            if config.get('query'):
                return _query_tables(data_file, data_format, has_header, config['query'])
            else:
                return _load_tables(data_file, data_format, has_header, load_kwargs)
        else:
            return load_data(data_file, format=data_format, has_header=has_header, **load_kwargs)

    if data_part:
        return load_data(StringIO(data_part), format=data_format or DEFAULT_FORMAT, has_header=has_header, **load_kwargs)

    return []
