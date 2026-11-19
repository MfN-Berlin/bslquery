from datetime import datetime

from bslquery.BioSoundsLabBase import BioSoundsLabBase
from bslquery import queries
from bslquery.decorators import db_query

class BioSoundsLabDB(BioSoundsLabBase):
    """
    A class to query the BioSoundsLab database.
    Inherits __init__, _log, _connect, test_connection and _fetchone_scalar
    from BioSoundsLabBase.
    """

    @db_query
    def fetch_site_id_by_prefix(self, cursor, prefix):
        """
        Get the site ids from the database
        prefix: text a site prefix, e.g. BBNSF_1205H
        returns: int id of the site, if found
        """
        cursor.execute(queries.FETCH_SITE_ID_BY_PREFIX, (f"%{prefix}%",))
        return self._fetchone_scalar(cursor)

    @staticmethod
    def days_between_dates(datestr1, datestr2):
        """
        Helper function to count days between dates.
        The start date and the end date are included in the count.
        This method does not query the database. To get the number of dates with a recording, use days_with_recordings instead.
        Static: callable as BioSoundsLabDB.days_between_dates(...) without an instance.

        date1, date2: string in the form YYYY-MM-DD
        return int number of days between dates
        """
        date1 = datetime.strptime(datestr1, '%Y-%m-%d')
        date2 = datetime.strptime(datestr2, '%Y-%m-%d')
        # Calculate the difference
        delta = abs((date2 - date1).days) + 1

        # Get the absolute number of days
        return delta


    @db_query
    def days_with_recordings(self, cursor, start_date, end_date, site_id):
        """
        Number of days where a recording was made on this site between these dates.
        The number of days is counted from the recordings in the database, independently of the
        inference parameters (model, species, threshold are NOT considered).

        date1, date2: string in the form YYYY-MM-dd
        site_id: int id in the sites table in the database
        return int days count
        """
        params = {
            "site_id": site_id, "start_date": start_date, "end_date": end_date,
        }
        cursor.execute(queries.DAYS_WITH_RECORDINGS, params)
        return self._fetchone_scalar(cursor)


    def fetch_combined_counts_breeding_season(self, species_name, site_prefix, start_date_breeding_season, end_date_breeding_season):
        """
        Combined days in breeding season and days with recordings.
        The purpose of this query is to compare recordings counts within a period of time, mostly the breeding season.

        Parameters:
        * species_name string: scientific name ScientificName_IOC10.1
        * site_prefix string: site prefix, e.g. BBBRI01
        * start_date_breeding_season string: date string (YYYY-MM-DD),
        * end_date_breeding_season: date string (YYYY-MM-DD)

        returns a dict in the form:
        ScientificName_IOC10.1, a string
        StartDate breeding season (MM-DD),
        EndDate breeding season (MM-DD),
        Days in breeding season (one column for each year),
        Site prefix year recording count (one column for each combination of prefix and year)
        """
        values = {
            'species_name': species_name,
            'site_prefix': site_prefix,
            'start_date_breeding_season': start_date_breeding_season,
            'end_date_breeding_season': end_date_breeding_season,
        }
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        values['days_in_breeding_season'] = self.days_between_dates(
            values['start_date_breeding_season'], values['end_date_breeding_season']
        )
        values['days_with_recordings'] = self.days_with_recordings(
            values['start_date_breeding_season'], values['end_date_breeding_season'], site_id
        )
        return values


    @db_query
    def fetch_acoustic_activity_counts(self, cursor, species_name, model_name, threshold, site_prefix, start_date, end_date):
        """
        Reads from the database the count of minutes with acoustic activity
        for this combination of parameters:

        species_name: scientific name of a species
        model_name: name of a model as stored in the database
        threshold: float threshold for this species and model
        site_prefix: prefix in the sites table in the database
        start_date: string YYYY-MM-DD start date of the breeding season,
        end_date: string YYYY-MM-DD end date of the breeding season, will be expanded to YYYY-MM-DD 23:59.59 +01:00

        returns: int counts
        """
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        label_id = self.fetch_label_id_by_species_name(species_name)
        model_id = self.fetch_model_id_by_model_name(model_name)
        params = {
            "site_id": site_id,
            "start_date": f"{start_date}T00:00:00+01:00",
            "end_date": f"{end_date}T23:59:59+01:00",
            "threshold": threshold, "label_id": label_id, "model_id": model_id
        }
        cursor.execute(queries.FETCH_ACOUSTIC_ACTIVITY_COUNTS, params)
        return self._fetchone_scalar(cursor)


    @db_query
    def fetch_count_acoustic_activity_days(self, cursor,
        species_name,
        model_name,
        threshold,
        site_prefix,
        start_date, end_date
    ):
        """
        Fetches the number of days whith acoustic activity of a species, above the threshold, for
        specific location, between 2 dates (e.g. for counting days where a bird sang during the
        breeding season).

        species_name: scientific name of a species
        model_name: name of a model as stored in the database
        threshold: float threshold for this species and model
        site_prefix: prefix in the sites table in the database
        start_date: string YYYY-MM-DD start date of the breeding season,
        end_date: string YYYY-MM-DD end date of the breeding season, will be expanded to YYYY-MM-DD 23:59.59 +01:00

        returns: int counts
        """
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        label_id = self.fetch_label_id_by_species_name(species_name)
        model_id = self.fetch_model_id_by_model_name(model_name)
        params = {
            "site_id": site_id,
            "label_id": label_id,
            "model_id": model_id,
            "start_date": f"{start_date}T00:00:00+01:00",
            "end_date": f"{end_date}T23:59:59+01:00",
            "threshold": threshold,
        }
        cursor.execute(queries.FETCH_COUNT_ACOUSTIC_ACTIVITY_DAYS, params)
        return self._fetchone_scalar(cursor)

    @db_query
    def count_species_with_threshold(self, cursor, site_prefix, model_name, threshold=0.5):
        """
        Counts the number of species in a site above a threshold.

        site_prefix: prefix in the sites table in the database
        model_name: name of a model as stored in the database
        threshold: float threshold for this species and model
        returns: int
        """
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        model_id = self.fetch_model_id_by_model_name(model_name)
        params = {
            "site_id": site_id,
            "model_id": model_id,
            "threshold": threshold
        }
        cursor.execute(queries.COUNT_SPECIES_WITH_THRESHOLD, params)
        return self._fetchone_scalar(cursor)


    @db_query
    def fetch_species_with_threshold(self, cursor, site_prefix, model_name, threshold=0.5):
        """
        Gets the species in a site above a threshold.
        Returns the entry with the highest confidence, one entry per species.

        site_prefix: prefix in the sites table in the database
        model_name: name of a model as stored in the database
        threshold: float threshold for this species and model
        returns: list of dict
        """
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        model_id = self.fetch_model_id_by_model_name(model_name)
        params = {
            "site_id": site_id,
            "model_id": model_id,
            "threshold": threshold
        }
        cursor.execute(queries.FETCH_SPECIES_WITH_THRESHOLD, params)
        return self._rows_as_dicts(cursor)


    @db_query
    def sites(self, cursor):
        """
        Fetches all sites in the database.
        Returns: list of dict
        """
        cursor.execute(queries.SITES)
        return self._rows_as_dicts(cursor)

    @db_query
    def fetch_thresholds(self, cursor, species_name, model_name):
        """
        Fetches the experimental, preliminary and final threshold
        for this species and model.
        If there are multiple values within a category, return only the latest.
        Returns dict with keys 'experimental', 'preliminary', 'final';
        missing types get None.
        """
        label_id = self.fetch_label_id_by_species_name(species_name)
        model_id = self.fetch_model_id_by_model_name(model_name)
        cursor.execute(queries.FETCH_THRESHOLDS, {"label_id": label_id, "model_id": model_id})
        return {
            "experimental": None,
            "preliminary":  None,
            "final":        None,
        } | dict(cursor.fetchall())   # overwrites found types

    @db_query
    def fetch_inferences(self, cursor, species_name, model_name, site_prefix, year, min_confidence=0):
        """
        Fetch all inferences for this combination of species, site and year.
        Returns: list of dict
        """
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        label_id = self.fetch_label_id_by_species_name(species_name)
        model_id = self.fetch_model_id_by_model_name(model_name)
        print(f"Processing: {site_prefix} ({site_id}), {year}, {species_name} ({label_id}), {model_name} ({model_id})")
        params = {
            "site_id": site_id,
            "year": year,
            "label_id":label_id,
            "model_id": model_id,
            "min_confidence": min_confidence
        }
        cursor.execute(queries.FETCH_INFERENCES, params)
        results = self._rows_as_dicts(cursor)
        if results is None:
            print("Found no results")
            return None
        print("Found %d results" % len(results))
        return results


    @db_query
    def fetch_max_pro_record(self, cursor, species_name, model_name, site_prefix, year, min_confidence=0):
        """
        Fetch all max pro record inferences for this combination of species, site and year.
        Returns: list of dict
        """
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        label_id = self.fetch_label_id_by_species_name(species_name)
        model_id = self.fetch_model_id_by_model_name(model_name)
        print(f"Processing: {site_prefix} ({site_id}), {year}, {species_name} ({label_id}), {model_name} ({model_id})")
        params = {
            "site_id": site_id,
            "year": year,
            "label_id":label_id,
            "model_id": model_id,
            "min_confidence": min_confidence
        }
        cursor.execute(queries.FETCH_MAX_PRO_RECORD, params)
        results = self._rows_as_dicts(cursor)
        if results is None:
            print("Found no results")
            return None
        print("Found %d results" % len(results))
        return results
