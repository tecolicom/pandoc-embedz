"""Data loading module for pandoc-embedz

Handles loading data from various formats using a dispatch table pattern.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from functools import partial
import pandas as pd
import yaml
import json
import sqlite3
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

def _load_json(source: Union[str, StringIO], **kwargs) -> Union[List[Any], Dict[str, Any]]:
    """Load JSON format"""
    if isinstance(source, StringIO):
        return json.loads(source.getvalue())
    with open(source, 'r', encoding='utf-8') as f:
        return json.load(f)

def _load_yaml(source: Union[str, StringIO], **kwargs) -> Union[List[Any], Dict[str, Any]]:
    """Load YAML format"""
    if isinstance(source, StringIO):
        return yaml.safe_load(source.getvalue())
    with open(source, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def _load_toml(source: Union[str, StringIO], **kwargs) -> Dict[str, Any]:
    """Load TOML format"""
    if tomllib is None:
        raise ImportError(
            "TOML support requires 'tomli' package for Python < 3.11. "
            "Install with: pip install tomli"
        )
    if isinstance(source, StringIO):
        return tomllib.loads(source.getvalue())
    with open(source, 'rb') as f:
        return tomllib.load(f)

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
            cursor.execute(f"SELECT * FROM {table}")

        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def _load_lines(source: Union[str, StringIO], **kwargs) -> List[str]:
    """Load plain text lines"""
    if isinstance(source, StringIO):
        lines = source.getvalue().splitlines()
    else:
        with open(source, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
    return [line for line in lines if line.strip()]

def _load_csv(
    source: Union[str, StringIO],
    sep: str = ',',
    has_header: bool = True,
    **kwargs
) -> Union[List[Dict[str, Any]], List[List[Any]]]:
    """Load CSV/TSV/SSV format with optional SQL query support"""
    read_kwargs = {'sep': sep}
    if sep == r'\s+':
        read_kwargs['engine'] = 'python'

    if has_header:
        df = pd.read_csv(source, **read_kwargs)
        if 'query' in kwargs:
            return _apply_sql_query(df, kwargs['query'])
        return df.to_dict('records')
    else:
        df = pd.read_csv(source, header=None, **read_kwargs)
        return df.values.tolist()

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
        source: File path or StringIO object
        format: Data format (csv, tsv, ssv, json, yaml, toml, sqlite, lines)
               If None, auto-detect from filename
        has_header: Whether CSV/TSV/SSV has header row
        **kwargs: Format-specific options (e.g., table/query for sqlite)

    Returns:
        Loaded data (list or dict depending on format)
    """
    from .config import validate_file_path

    if isinstance(source, str):
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
        read_kwargs = {'header': 0 if has_header else None}
        if sep == r'\s+':
            read_kwargs['engine'] = 'python'

        tables[table_name] = pd.read_csv(source, sep=sep, **read_kwargs)

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
