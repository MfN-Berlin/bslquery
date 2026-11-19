import json
import logging
from pathlib import Path

import jsonschema

# the logger is tied to the module, not the class (Pythonesque way)
logger = logging.getLogger(__name__)


class DwCValidator:
    """
    Validates Darwin Core (DwC) data against the BioSoundsLab occurrence PAM
    schema (schema/dwc-occurrence-pam.schema.json).

    Pure JSON-schema checking: no database connection is needed, so this
    deliberately does NOT extend BioSoundsLabBase.
    """
    # repo-root schema/, resolved from this file so it works from any CWD
    SCHEMA_FILE = Path(__file__).resolve().parents[2] / "schema" / "dwc-occurrence-pam.schema.json"

    def __init__(self, verbose=False):
        self.verbose = verbose  # If True, print messages to stdout (for Jupyter)

    def _log(self, message, level=logging.INFO):
        """Log a message, and print if verbose is True."""
        if self.verbose:
            print(message)
        if level == logging.ERROR:
            logger.error(message)
        else:
            logger.info(message)

    def validate(self, data):
        """
        Validate Darwin Core (DwC) data against the BioSoundsLab occurrence PAM
        schema. `data` is a list of occurrence records, e.g. the result of
        BioSoundsLabDwC.fetch_inferences.
        Returns: True if the data is valid, False otherwise (errors are logged).
        """
        with open(self.SCHEMA_FILE) as f:
            schema = json.load(f)
        validator = jsonschema.Draft7Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        for e in errors:
            self._log(f"DwC validation error at {list(e.absolute_path)}: {e.message}", level=logging.ERROR)
        return not errors
