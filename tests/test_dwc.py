"""Tests for BioSoundsLabDwC: fetch_inferences returns Darwin Core occurrence records.

Uses the fake connector from conftest.py; the id lookups run against the
fake cursor too, so fetchone is stubbed to return the ids in order.
"""

import json
from datetime import date, time

import psycopg2
import pytest

from bslquery.BioSoundsLabDwC import BioSoundsLabDwC
from conftest import FakeConnection

COLUMNS = [
    "site_prefix", "site_name", "date", "time", "filename",
    "start_time", "end_time", "model_name", "species", "confidence",
    "experimental_threshold", "preliminary_threshold", "final_threshold",
]

DWC_KEYS = {
    "occurrenceID", "eventID", "eventDate", "eventTime", "scientificName",
    "taxonRank", "occurrenceStatus", "basisOfRecord", "recordedBy",
    "locationID", "locality", "dynamicProperties",
}


@pytest.fixture
def dwc(monkeypatch, cursor):
    """A BioSoundsLabDwC instance whose _connect() returns a FakeConnection wrapping `cursor`."""
    conn = FakeConnection(cursor)
    monkeypatch.setattr(BioSoundsLabDwC, "_connect", lambda self: conn)
    return BioSoundsLabDwC({"host": "fake-host"}, verbose=False)


@pytest.fixture
def ids(cursor):
    """fetchone() returns site, label and model ids in order for the 3 lookup queries."""
    values = iter([(11,), (22,), (33,)])
    cursor.fetchone = lambda: next(values)


class TestFetchInferencesDWC:
    def test_rows_mapped_to_darwin_core(self, dwc, cursor, ids):
        cursor.description = [(c,) for c in COLUMNS]
        cursor.fetchall_result = [
            ("BBNSF", "Site North", date(2024, 5, 1), time(6, 30), "rec01.wav",
             0.0, 5.0, "BirdNET+", "Anthus trivialis", 0.97, 0.5, 0.6, 0.9),
            ("BBNSF", "Site North", date(2024, 5, 2), time(6, 30), "rec02.wav",
             1.5, 9.0, "BirdNET+", "Anthus trivialis", 0.88, 0.5, 0.6, 0.9),
        ]
        result = dwc.fetch_inferences("Anthus trivialis", "BirdNET+", "BBNSF", 2024, min_confidence=0.5)

        assert len(result) == 2
        first = result[0]
        assert set(first.keys()) == DWC_KEYS
        assert first["occurrenceID"] == "rec01.wav#0.0"
        assert first["eventID"] == "rec01.wav"
        assert first["eventDate"] == "2024-05-01"
        assert first["eventTime"] == "06:30:00"
        assert first["scientificName"] == "Anthus trivialis"
        assert first["taxonRank"] == "species"
        assert first["occurrenceStatus"] == "present"
        assert first["basisOfRecord"] == "MachineObservation"
        assert first["recordedBy"] == "BirdNET+"
        assert first["locationID"] == "BBNSF"
        assert first["locality"] == "Site North"
        props = json.loads(first["dynamicProperties"])
        assert props == {
            "start_time": "0.0", "end_time": "5.0", "confidence": 0.97,
            "experimental_threshold": 0.5, "preliminary_threshold": 0.6, "final_threshold": 0.9,
        }
        assert result[1]["occurrenceID"] == "rec02.wav#1.5"

    def test_main_query_params_wired(self, dwc, cursor, ids):
        cursor.description = [(c,) for c in COLUMNS]
        cursor.fetchall_result = []
        dwc.fetch_inferences("Anthus trivialis", "BirdNET+", "BBNSF", 2024, min_confidence=0.5)
        # the 3 lookups ran first, then the main query
        query, params = cursor.executed[-1]
        assert "model_inference_results_view" in query
        assert params == {"site_id": 11, "year": 2024, "label_id": 22, "model_id": 33, "min_confidence": 0.5}

    def test_no_rows_returns_none(self, dwc, cursor, ids):
        cursor.description = [(c,) for c in COLUMNS]
        cursor.fetchall_result = []
        assert dwc.fetch_inferences("Anthus trivialis", "BirdNET+", "BBNSF", 2024) is None

    def test_default_min_confidence_is_zero(self, dwc, cursor, ids):
        cursor.description = [(c,) for c in COLUMNS]
        cursor.fetchall_result = []
        dwc.fetch_inferences("Anthus trivialis", "BirdNET+", "BBNSF", 2024)
        _, params = cursor.executed[-1]
        assert params["min_confidence"] == 0

    def test_query_error_returns_none(self, dwc, cursor, ids):
        cursor.execute_error = psycopg2.DatabaseError("boom")
        assert dwc.fetch_inferences("Anthus trivialis", "BirdNET+", "BBNSF", 2024) is None
