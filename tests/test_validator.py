"""Tests for DwCValidator: validate() checks DwC data against the PAM schema.

The valid sample is embedded below as JSON text, so these tests do not
depend on files in examples/. No database involved: validate() is pure
JSON-schema checking.
"""

import json

import pytest

from bslquery.DwCValidator import DwCValidator

VALID_DWC_JSON = """
[
  {
    "occurrenceID": "AKWAMO9801G_20240411_130000.wav#24.0",
    "eventID": "AKWAMO9801G_20240411_130000.wav",
    "eventDate": "2024-04-11",
    "eventTime": "13:00:00",
    "scientificName": "Falco subbuteo",
    "taxonRank": "species",
    "occurrenceStatus": "present",
    "basisOfRecord": "MachineObservation",
    "recordedBy": "BNP_v3_0_glob11k_prev3_cw5s_sz2s",
    "locationID": "AKWAMO9801G",
    "locality": "Britz, BBBRI_9801G",
    "dynamicProperties": "{\\"start_time\\": \\"24.0\\", \\"end_time\\": \\"29.0\\", \\"confidence\\": 0.01676, \\"experimental_threshold\\": null, \\"preliminary_threshold\\": null, \\"final_threshold\\": null}"
  }
]
"""


@pytest.fixture
def validator():
    # standalone validator: no db_config, validate() never opens a connection
    return DwCValidator(verbose=False)


def test_schema_file_exists():
    assert DwCValidator.SCHEMA_FILE.is_file(), f"schema missing: {DwCValidator.SCHEMA_FILE}"


def test_valid_occurrence_array_is_valid(validator):
    assert validator.validate(json.loads(VALID_DWC_JSON)) is True


def test_missing_required_field_is_invalid(validator):
    data = json.loads(VALID_DWC_JSON)
    del data[0]["scientificName"]  # required by the schema
    assert validator.validate(data) is False


def test_bad_enum_value_is_invalid(validator):
    data = json.loads(VALID_DWC_JSON)
    data[0]["occurrenceStatus"] = "maybe"  # not in the schema enum
    assert validator.validate(data) is False


def test_top_level_must_be_array(validator):
    assert validator.validate({"occurrenceID": "x"}) is False
