"""Error-path tests: no real database, the fake connector raises instead.

Every query method must catch psycopg2 errors, log them, and return None
(test_connection returns False). fetch_combined_counts_breeding_season is
the exception: it returns a dict whose 'days_with_recordings' is None.
"""

import logging

import psycopg2
import pytest

from bslquery.BioSoundsLabDB import BioSoundsLabDB

LOGGER = "bslquery.BioSoundsLabDB"

# (method name, args) for every method that opens a connection and queries
QUERY_METHODS = [
    ("fetch_site_id_by_prefix", ("BBNSF",)),
    ("fetch_label_id_by_species_name", ("Anthus trivialis",)),
    ("fetch_model_id_by_model_name", ("BirdNET+",)),
    ("days_with_recordings", ("2024-05-01", "2024-08-31", 11)),
    ("fetch_acoustic_activity_counts", ("Anthus trivialis", "BirdNET+", 0.7, "BBNSF", "2024-05-01", "2024-08-31")),
    ("fetch_count_acoustic_activity_days", ("Anthus trivialis", "BirdNET+", 0.7, "BBNSF", "2024-05-01", "2024-08-31")),
    ("count_species_with_threshold", ("BBNSF", "BirdNET+")),
    ("fetch_species_with_threshold", ("BBNSF", "BirdNET+")),
    ("sites", ()),
    ("sites_years", ()),
    ("fetch_thresholds", ("Anthus trivialis", "BirdNET+")),
    ("fetch_inferences", ("Anthus trivialis", "BirdNET+", "BBNSF", 2024)),
    ("fetch_max_pro_record", ("Anthus trivialis", "BirdNET+", "BBNSF", 2024)),
]

ERRORS = [psycopg2.OperationalError, psycopg2.DatabaseError]


def _raise(exc):
    """Build a replacement for _connect that raises exc."""
    def raiser(self):
        raise exc
    return raiser


@pytest.mark.parametrize("method_name,args", QUERY_METHODS)
@pytest.mark.parametrize("error", ERRORS, ids=["operational", "database"])
def test_execute_error_returns_none_and_logs(db, cursor, caplog, method_name, args, error):
    cursor.execute_error = error("boom")
    with caplog.at_level(logging.INFO, logger=LOGGER):
        result = getattr(db, method_name)(*args)
    assert result is None
    assert any(
        r.levelno >= logging.INFO and "failed" in r.getMessage().lower()
        for r in caplog.records
    )


@pytest.mark.parametrize("method_name,args", QUERY_METHODS)
@pytest.mark.parametrize("error", ERRORS, ids=["operational", "database"])
def test_connect_error_returns_none_and_logs(db, monkeypatch, caplog, method_name, args, error):
    monkeypatch.setattr(BioSoundsLabDB, "_connect", _raise(error("no server")))
    with caplog.at_level(logging.INFO, logger=LOGGER):
        result = getattr(db, method_name)(*args)
    assert result is None
    # both error branches log a message containing "failed":
    # "Connection failed" (OperationalError) and "Query failed" (DatabaseError)
    assert any("failed" in r.getMessage().lower() for r in caplog.records)


@pytest.mark.parametrize("error,expected", [
    (psycopg2.OperationalError, "connection failed"),
    (psycopg2.DatabaseError, "database error"),
], ids=["operational", "database"])
def test_test_connection_connect_error_returns_false(db, monkeypatch, caplog, error, expected):
    monkeypatch.setattr(BioSoundsLabDB, "_connect", _raise(error("no server")))
    with caplog.at_level(logging.INFO, logger=LOGGER):
        result = db.test_connection()
    assert result is False
    assert any(expected in r.getMessage().lower() for r in caplog.records)


@pytest.mark.parametrize("error", ERRORS, ids=["operational", "database"])
def test_combined_counts_with_db_error_returns_dict_with_none_recordings(db, monkeypatch, error):
    monkeypatch.setattr(BioSoundsLabDB, "_connect", _raise(error("no server")))
    result = db.fetch_combined_counts_breeding_season(
        "Anthus trivialis", "BBNSF", "2024-04-01", "2024-04-10"
    )
    assert result["days_in_breeding_season"] == 10  # pure date math still works
    assert result["days_with_recordings"] is None    # the query failed
