"""Tests for logic that never touches the database.

These construct BioSoundsLabDB directly: the constructor only stores the
config, so no connection is opened and the fake connector is not needed.
"""

import logging

import pytest

from bslquery.BioSoundsLabDB import BioSoundsLabDB


@pytest.fixture
def db():
    return BioSoundsLabDB({"host": "unused"}, verbose=False)


class TestDaysBetweenDates:
    def test_same_day_counts_one(self, db):
        assert db.days_between_dates("2024-05-05", "2024-05-05") == 1

    def test_both_endpoints_included(self, db):
        assert db.days_between_dates("2024-01-01", "2024-01-31") == 31

    def test_reversed_arguments_give_same_result(self, db):
        assert db.days_between_dates("2024-01-31", "2024-01-01") == 31

    def test_across_year_boundary(self, db):
        assert db.days_between_dates("2023-12-30", "2024-01-02") == 4

    def test_leap_year_february(self, db):
        assert db.days_between_dates("2024-02-01", "2024-02-29") == 29

    def test_invalid_date_format_raises(self, db):
        with pytest.raises(ValueError):
            db.days_between_dates("05/01/2024", "2024-01-31")


class TestLog:
    def test_verbose_prints_to_stdout(self, capsys):
        db = BioSoundsLabDB({"host": "unused"}, verbose=True)
        db._log("hello")
        assert "hello" in capsys.readouterr().out

    def test_not_verbose_does_not_print(self, capsys, db):
        db._log("hello")
        assert capsys.readouterr().out == ""

    def test_error_level_logged_as_error(self, caplog, db):
        with caplog.at_level(logging.ERROR, logger="bslquery.BioSoundsLabDB"):
            db._log("boom", level=logging.ERROR)
        assert "boom" in caplog.text
        assert any(r.levelno == logging.ERROR for r in caplog.records)

    def test_info_level_not_logged_as_error(self, caplog, db):
        with caplog.at_level(logging.INFO, logger="bslquery.BioSoundsLabDB"):
            db._log("note")
        assert any(r.levelno == logging.INFO for r in caplog.records)
        assert not any(r.levelno == logging.ERROR for r in caplog.records)
