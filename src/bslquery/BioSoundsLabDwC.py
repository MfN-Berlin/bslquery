import json

from bslquery import queries
from bslquery.BioSoundsLabBase import BioSoundsLabBase
from bslquery.decorators import db_query


class BioSoundsLabDwC(BioSoundsLabBase):
    """
    A class to query the BioSoundsLab database for Darwin Core (DwC) data.
    Inherits __init__, _log, _connect and test_connection from BioSoundsLabBase.
    SQL is accessed through the bslquery.queries package (queries.<NAME>),
    the single place where .sql files are loaded.
    """

    @staticmethod
    def _row_to_dwc(row):
        """Map one inference row (dict of column name -> value) to a Darwin Core
        Occurrence record: DwC term names as keys, non-DwC extras (confidence,
        thresholds, segment times) packed into dynamicProperties as JSON."""
        return {
            "occurrenceID": f"{row['filename']}#{row['start_time']}",
            "eventID": row["filename"],
            "eventDate": str(row["date"]),
            "eventTime": str(row["time"]),
            "scientificName": row["species"],
            "taxonRank": "species",
            "occurrenceStatus": "present",
            "basisOfRecord": "MachineObservation",
            "recordedBy": row["model_name"],
            "locationID": row["site_prefix"],
            "locality": row["site_name"],
            "dynamicProperties": json.dumps({
                "start_time": str(row["start_time"]),
                "end_time": str(row["end_time"]),
                "confidence": row["confidence"],
                "experimental_threshold": row["experimental_threshold"],
                "preliminary_threshold": row["preliminary_threshold"],
                "final_threshold": row["final_threshold"],
            }),
        }


    @db_query
    def fetch_inferences(self, cursor, species_name, model_name, site_prefix, year, min_confidence=0):
        """
        Fetch all inferences for this combination of species, site and year.
        Returns: list of dict, one Darwin Core occurrence record per inference
        row (see _row_to_dwc), or None if there are no results.
        """
        cursor.execute(queries.FETCH_SITE_ID_BY_PREFIX, (f"%{site_prefix}%",))
        site_id = self._fetchone_scalar(cursor)
        cursor.execute(queries.FETCH_LABEL_ID_BY_SPECIES_NAME, (f"%{species_name}%",))
        label_id = self._fetchone_scalar(cursor)
        cursor.execute(queries.FETCH_MODEL_ID_BY_MODEL_NAME, (f"%{model_name}%",))
        model_id = self._fetchone_scalar(cursor)
        print(f"Processing: {site_prefix} ({site_id}), {year}, {species_name} ({label_id}), {model_name} ({model_id})")
        params = {
            "site_id": site_id,
            "year": year,
            "label_id": label_id,
            "model_id": model_id,
            "min_confidence": min_confidence
        }
        cursor.execute(queries.FETCH_INFERENCES, params)
        rows = cursor.fetchall()
        if not rows:
            print("Found no results")
            return None
        columns = [d[0] for d in cursor.description]
        results = [self._row_to_dwc(dict(zip(columns, row))) for row in rows]
        print("Found %d results" % len(results))
        return results
