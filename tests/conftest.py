"""Shared pytest fixtures: fake psycopg2 connection/cursor so unit tests need no database."""

import pytest

from bslquery.BioSoundsLabDB import BioSoundsLabDB


class FakeCursor:
    """Mimics a psycopg2 cursor.

    Configure the results (fetchone_result, fetchall_result, description),
    call a method under test, then inspect `executed` to assert on the
    query and params that were passed.
    """

    def __init__(self):
        self.executed = []          # list of (query, params) passed to execute()
        self.fetchone_result = None  # value returned by fetchone()
        self.fetchall_result = []    # value returned by fetchall()
        self.description = None      # e.g. [("prefix",), ("name",)]; desc[0] is the column name
        self.execute_error = None    # exception instance raised by execute(), if set

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        if self.execute_error is not None:
            raise self.execute_error
        self.executed.append((query, params))

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_result


class FakeConnection:
    """Mimics a psycopg2 connection; cursor() always returns the same FakeCursor."""

    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self._cursor


@pytest.fixture
def cursor():
    """A fresh FakeCursor for each test."""
    return FakeCursor()


@pytest.fixture
def db(monkeypatch, cursor):
    """A BioSoundsLabDB instance whose _connect() returns a FakeConnection wrapping `cursor`."""
    conn = FakeConnection(cursor)
    monkeypatch.setattr(BioSoundsLabDB, "_connect", lambda self: conn)
    return BioSoundsLabDB({"host": "fake-host"}, verbose=False)
