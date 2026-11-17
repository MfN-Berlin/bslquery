"""Every @db_query method must have a matching, non-empty .sql file.

@db_query sets __wrapped__ via functools.wraps, so decorated methods are
identifiable; the constant in bslquery.queries is the method name uppercased.
"""

import inspect

import bslquery.queries as queries
from bslquery.BioSoundsLabDB import BioSoundsLabDB


def _db_query_methods():
    return [
        name
        for name, member in inspect.getmembers(BioSoundsLabDB, predicate=inspect.isfunction)
        if hasattr(member, "__wrapped__")
    ]


def test_every_db_query_method_has_a_sql_constant():
    methods = _db_query_methods()
    assert len(methods) == 13  # guard against silently losing a decorator
    for name in methods:
        sql = getattr(queries, name.upper(), None)
        assert sql is not None, f"bslquery.queries.{name.upper()} missing for {name}()"
        assert sql.strip(), f"queries/{name}.sql is empty"
        assert "%(" in sql or "%s" in sql or "SELECT" in sql.upper()
