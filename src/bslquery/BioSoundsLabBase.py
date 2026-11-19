import logging

import psycopg2
from psycopg2 import OperationalError, DatabaseError
from bslquery import queries
from bslquery.decorators import db_query


class BioSoundsLabBase:
    """
    Base class for BioSoundsLab database access.

    Holds the pieces shared by every subclass: configuration storage,
    logging, and the connection seam. _connect is concrete on purpose:
    subclasses inherit it as-is and only override it to change how
    connections are made.
    Note: might want to use a connection pool instead
    """
    def __init__(self, db_config, verbose=False):
        self.db_config = db_config
        self.verbose = verbose  # If True, print messages to stdout (for Jupyter)
        # logger tied to the concrete subclass's module (Pythonesque way),
        # so each subclass logs under its own name, e.g. bslquery.BioSoundsLabDB
        self._logger = logging.getLogger(type(self).__module__)


    def _log(self, message, level=logging.INFO):
        """Log a message, and print if verbose is True."""
        if self.verbose:
            print(message)
        if level == logging.ERROR:
            self._logger.error(message)
        else:
            self._logger.info(message)


    def _connect(self):
        """Open a new connection using self.db_config.

        Single seam patched in unit tests. Shared by all subclasses;
        override in a subclass only to change how connections are made.
        """
        return psycopg2.connect(**self.db_config)


    def test_connection(self):
        """
        Test if a connection to the PostgreSQL database can be established.
        db_config (dict): Database connection parameters (host, port, user, password, database).
        returns: True if the connection is successful, False otherwise.
        """
        try:
            with self._connect() as conn:
                self._log("Connection successful!")
                return True
        except OperationalError as e:
            self._log(f"Connection failed: {e}")
            return False
        except DatabaseError as e:
            self._log(f"Database error: {e}")
            return False


    @staticmethod
    def _fetchone_scalar(cursor):
        """fetchone() and return the first column, or None if there is no row."""
        row = cursor.fetchone()
        return row[0] if row else None


    @staticmethod
    def _rows_as_dicts(cursor):
        """fetchall() as a list of dicts keyed by column name, or None if no rows."""
        rows = cursor.fetchall()
        if not rows:
            return None                      # tests assert empty result -> None
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


    @db_query
    def sites_years(self, cursor):
        """
        Fetches all sites and years combinations in the database.
        Returns: list of dict
        """
        cursor.execute(queries.SITES_YEARS)
        return self._rows_as_dicts(cursor)

    @db_query
    def fetch_label_id_by_species_name(self, cursor, species_name):
        """
        Get from the database the labels corresponding to the species
        prefix: text a species name, e.g. Anthus trivialis
        returns: int id of the label, if found
        """
        cursor.execute(queries.FETCH_LABEL_ID_BY_SPECIES_NAME, (f"%{species_name}%",))
        return self._fetchone_scalar(cursor)


    @db_query
    def fetch_model_id_by_model_name(self, cursor, model_name):
        """
        Get from the database the model corresponding to the name
        prefix: text a model name, e.g. BirdNET+_v0.3_global11K_prev3
        returns: int id of the label, if found
        """
        cursor.execute(queries.FETCH_MODEL_ID_BY_MODEL_NAME, (f"%{model_name}%",))
        return self._fetchone_scalar(cursor)
