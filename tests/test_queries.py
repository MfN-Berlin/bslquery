"""Tests for the query methods, using the fake connector from conftest.py.

Covers return-value mapping (rows -> return values), parameter wiring
(what is passed to cursor.execute), and rows -> list of dicts.
"""

from datetime import date, time

import psycopg2
import pytest

from bslquery.BioSoundsLabDB import BioSoundsLabDB


def _raise(exc):
    """Build a replacement for _connect that raises exc."""
    def raiser(self):
        raise exc
    return raiser


class TestReturnValueMapping:
    def test_fetch_site_id_found(self, db, cursor):
        cursor.fetchone_result = (42,)
        assert db.fetch_site_id_by_prefix("BBNSF") == 42

    def test_fetch_site_id_not_found_returns_none(self, db, cursor):
        cursor.fetchone_result = None
        assert db.fetch_site_id_by_prefix("nope") is None

    def test_fetch_label_id(self, db, cursor):
        cursor.fetchone_result = (7,)
        assert db.fetch_label_id_by_species_name("Anthus trivialis") == 7

    def test_fetch_model_id(self, db, cursor):
        cursor.fetchone_result = (3,)
        assert db.fetch_model_id_by_model_name("BirdNET") == 3

    def test_days_with_recordings_returns_count(self, db, cursor):
        cursor.fetchone_result = (15,)
        assert db.days_with_recordings("2024-05-01", "2024-08-31", 11) == 15

    def test_test_connection_success(self, db):
        assert db.test_connection() is True

    def test_test_connection_operational_error_returns_false(self, db, monkeypatch):
        monkeypatch.setattr(BioSoundsLabDB, "_connect", _raise(psycopg2.OperationalError("refused")))
        assert db.test_connection() is False

    def test_query_error_returns_none(self, db, cursor):
        cursor.execute_error = psycopg2.DatabaseError("bad query")
        assert db.fetch_site_id_by_prefix("BBNSF") is None

    def test_fetch_thresholds_fills_missing_types_with_none(self, db, cursor):
        cursor.fetchone_result = (5,)  # returned by both id lookups
        cursor.fetchall_result = [("final", 0.9)]
        result = db.fetch_thresholds("Anthus trivialis", "BirdNET")
        assert result == {"experimental": None, "preliminary": None, "final": 0.9}


class TestParameterWiring:
    def test_site_prefix_wrapped_in_like_wildcards(self, db, cursor):
        db.fetch_site_id_by_prefix("BBNSF_1205H")
        _, params = cursor.executed[-1]
        assert params == ("%BBNSF_1205H%",)

    def test_days_with_recordings_passes_dates_unmodified(self, db, cursor):
        cursor.fetchone_result = (1,)
        db.days_with_recordings("2024-05-01", "2024-08-31", 11)
        _, params = cursor.executed[-1]
        assert params == {"site_id": 11, "start_date": "2024-05-01", "end_date": "2024-08-31"}

    def test_acoustic_activity_counts_expands_dates_to_full_day(self, db, cursor, monkeypatch):
        monkeypatch.setattr(db, "fetch_site_id_by_prefix", lambda prefix: 11)
        monkeypatch.setattr(db, "fetch_label_id_by_species_name", lambda name: 22)
        monkeypatch.setattr(db, "fetch_model_id_by_model_name", lambda name: 33)
        cursor.fetchone_result = (123,)
        result = db.fetch_acoustic_activity_counts(
            "Anthus trivialis", "BirdNET", 0.7, "BBNSF", "2024-05-01", "2024-08-31"
        )
        assert result == 123
        _, params = cursor.executed[-1]
        assert params == {
            "site_id": 11,
            "label_id": 22,
            "model_id": 33,
            "threshold": 0.7,
            "start_date": "2024-05-01T00:00:00+01:00",
            "end_date": "2024-08-31T23:59:59+01:00",
        }

    def test_count_species_default_threshold(self, db, cursor, monkeypatch):
        monkeypatch.setattr(db, "fetch_site_id_by_prefix", lambda prefix: 11)
        monkeypatch.setattr(db, "fetch_model_id_by_model_name", lambda name: 33)
        cursor.fetchone_result = (8,)
        assert db.count_species_with_threshold("BBNSF", "BirdNET") == 8
        _, params = cursor.executed[-1]
        assert params == {"site_id": 11, "model_id": 33, "threshold": 0.5}

    def test_fetch_thresholds_passes_ids(self, db, cursor):
        cursor.fetchone_result = (5,)
        cursor.fetchall_result = []
        db.fetch_thresholds("Anthus trivialis", "BirdNET")
        _, params = cursor.executed[-1]
        assert params == {"label_id": 5, "model_id": 5}


class TestRowsToDicts:
    def test_sites(self, db, cursor):
        cursor.description = [("prefix",), ("name",)]
        cursor.fetchall_result = [("BB01", "Site One"), ("BB02", "Site Two")]
        assert db.sites() == [
            {"prefix": "BB01", "name": "Site One"},
            {"prefix": "BB02", "name": "Site Two"},
        ]

    def test_sites_empty_returns_none(self, db, cursor):
        cursor.description = [("prefix",), ("name",)]
        cursor.fetchall_result = []
        assert db.sites() is None

    def test_sites_years(self, db, cursor):
        cursor.description = [("prefix",), ("name",), ("year",), ("count",)]
        cursor.fetchall_result = [("BB01", "Site One", 2023, 100), ("BB01", "Site One", 2024, 250)]
        assert db.sites_years() == [
            {"prefix": "BB01", "name": "Site One", "year": 2023, "count": 100},
            {"prefix": "BB01", "name": "Site One", "year": 2024, "count": 250},
        ]

    def test_fetch_species_with_threshold(self, db, cursor, monkeypatch):
        monkeypatch.setattr(db, "fetch_site_id_by_prefix", lambda prefix: 11)
        monkeypatch.setattr(db, "fetch_model_id_by_model_name", lambda name: 33)
        cursor.description = [("species",), ("confidence",)]
        cursor.fetchall_result = [("Anthus trivialis", 0.97), ("Turdus merula", 0.88)]
        result = db.fetch_species_with_threshold("BBNSF", "BirdNET", threshold=0.5)
        assert result == [
            {"species": "Anthus trivialis", "confidence": 0.97},
            {"species": "Turdus merula", "confidence": 0.88},
        ]
        _, params = cursor.executed[-1]
        assert params == {"site_id": 11, "model_id": 33, "threshold": 0.5}


class TestCombinedCounts:
    def test_assembles_dict_from_helpers(self, db, monkeypatch):
        monkeypatch.setattr(db, "fetch_site_id_by_prefix", lambda prefix: 11)
        monkeypatch.setattr(db, "days_with_recordings", lambda start, end, site_id: 12)
        result = db.fetch_combined_counts_breeding_season(
            "Anthus trivialis", "BBNSF", "2024-04-01", "2024-04-10"
        )
        assert result == {
            "species_name": "Anthus trivialis",
            "site_prefix": "BBNSF",
            "start_date_breeding_season": "2024-04-01",
            "end_date_breeding_season": "2024-04-10",
            "days_in_breeding_season": 10,
            "days_with_recordings": 12,
        }


class TestFetchInferences:
    """fetch_inferences against the fake cursor: no real database involved."""

    COLUMNS = [
        "site_prefix", "site_name", "date", "time", "filename",
        "start_time", "end_time", "model_name", "species", "confidence",
        "experimental_threshold", "preliminary_threshold", "final_threshold",
    ]

    @pytest.fixture
    def inferences_db(self, db, monkeypatch):
        """db with the id lookups stubbed, so the fake cursor only sees the main query."""
        monkeypatch.setattr(db, "fetch_site_id_by_prefix", lambda prefix: 11)
        monkeypatch.setattr(db, "fetch_label_id_by_species_name", lambda name: 22)
        monkeypatch.setattr(db, "fetch_model_id_by_model_name", lambda name: 33)
        return db

    def test_rows_mapped_to_dicts_and_params_wired(self, inferences_db, cursor):
        cursor.description = [(c,) for c in self.COLUMNS]
        cursor.fetchall_result = [
            ("BBNSF", "Site North", date(2024, 5, 1), time(6, 30), "rec01.wav",
             0.0, 5.0, "BirdNET+", "Anthus trivialis", 0.97, 0.5, 0.6, 0.9),
            ("BBNSF", "Site North", date(2024, 5, 2), time(6, 30), "rec02.wav",
             1.5, 9.0, "BirdNET+", "Anthus trivialis", 0.88, 0.5, 0.6, 0.9),
        ]
        result = inferences_db.fetch_inferences(
            "Anthus trivialis", "BirdNET+", "BBNSF", 2024, min_confidence=0.5
        )
        assert result == [
            {"site_prefix": "BBNSF", "site_name": "Site North", "date": date(2024, 5, 1),
             "time": time(6, 30), "filename": "rec01.wav", "start_time": 0.0, "end_time": 5.0,
             "model_name": "BirdNET+", "species": "Anthus trivialis", "confidence": 0.97,
             "experimental_threshold": 0.5, "preliminary_threshold": 0.6, "final_threshold": 0.9},
            {"site_prefix": "BBNSF", "site_name": "Site North", "date": date(2024, 5, 2),
             "time": time(6, 30), "filename": "rec02.wav", "start_time": 1.5, "end_time": 9.0,
             "model_name": "BirdNET+", "species": "Anthus trivialis", "confidence": 0.88,
             "experimental_threshold": 0.5, "preliminary_threshold": 0.6, "final_threshold": 0.9},
        ]
        query, params = cursor.executed[-1]
        assert params == {
            "site_id": 11, "year": 2024, "label_id": 22,
            "model_id": 33, "min_confidence": 0.5,
        }
        assert "%(min_confidence)s" in query

    def test_no_rows_returns_none(self, inferences_db, cursor):
        cursor.description = [(c,) for c in self.COLUMNS]
        cursor.fetchall_result = []
        assert inferences_db.fetch_inferences("Anthus trivialis", "BirdNET+", "BBNSF", 2024) is None

    def test_default_min_confidence_is_zero(self, inferences_db, cursor):
        cursor.description = [(c,) for c in self.COLUMNS]
        cursor.fetchall_result = []
        inferences_db.fetch_inferences("Anthus trivialis", "BirdNET+", "BBNSF", 2024)
        _, params = cursor.executed[-1]
        assert params["min_confidence"] == 0


class TestFetchMaxProRecord:
    """fetch_max_pro_record against the fake cursor: no real database involved."""

    COLUMNS = TestFetchInferences.COLUMNS  # same selected columns as fetch_inferences

    @pytest.fixture
    def maxpro_db(self, db, monkeypatch):
        """db with the id lookups stubbed, so the fake cursor only sees the main query."""
        monkeypatch.setattr(db, "fetch_site_id_by_prefix", lambda prefix: 11)
        monkeypatch.setattr(db, "fetch_label_id_by_species_name", lambda name: 22)
        monkeypatch.setattr(db, "fetch_model_id_by_model_name", lambda name: 33)
        return db

    def test_rows_mapped_to_dicts_and_params_wired(self, maxpro_db, cursor):
        cursor.description = [(c,) for c in self.COLUMNS]
        cursor.fetchall_result = [
            ("BBNSF", "Site North", date(2024, 5, 1), time(6, 30), "rec01.wav",
             0.0, 15.0, "BirdNET+", "Anthus trivialis", 0.99, 0.5, 0.6, 0.9),
        ]
        result = maxpro_db.fetch_max_pro_record(
            "Anthus trivialis", "BirdNET+", "BBNSF", 2024, min_confidence=0.8
        )
        assert result == [
            {"site_prefix": "BBNSF", "site_name": "Site North", "date": date(2024, 5, 1),
             "time": time(6, 30), "filename": "rec01.wav", "start_time": 0.0, "end_time": 15.0,
             "model_name": "BirdNET+", "species": "Anthus trivialis", "confidence": 0.99,
             "experimental_threshold": 0.5, "preliminary_threshold": 0.6, "final_threshold": 0.9},
        ]
        query, params = cursor.executed[-1]
        assert params == {
            "site_id": 11, "year": 2024, "label_id": 22,
            "model_id": 33, "min_confidence": 0.8,
        }
        assert "model_inference_results_max_confidence" in query
        assert "model_inference_results_view" not in query

    def test_no_rows_returns_none(self, maxpro_db, cursor):
        cursor.description = [(c,) for c in self.COLUMNS]
        cursor.fetchall_result = []
        assert maxpro_db.fetch_max_pro_record("Anthus trivialis", "BirdNET+", "BBNSF", 2024) is None

    def test_default_min_confidence_is_zero(self, maxpro_db, cursor):
        cursor.description = [(c,) for c in self.COLUMNS]
        cursor.fetchall_result = []
        maxpro_db.fetch_max_pro_record("Anthus trivialis", "BirdNET+", "BBNSF", 2024)
        _, params = cursor.executed[-1]
        assert params["min_confidence"] == 0
