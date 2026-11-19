import logging

import psycopg2


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
