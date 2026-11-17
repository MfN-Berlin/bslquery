import psycopg2
from psycopg2 import OperationalError, DatabaseError
from datetime import datetime
import logging

# the logger is tied too the module, not the class (Pythonesque way)
# __name__ is the name of the module
logger = logging.getLogger(__name__)

class BioSoundsLabDB:
    """
    A class to query the BioSoundsLab database.
    Note: might want to use a connection pool instead
    """
    def __init__(self, db_config, verbose=False):
        self.db_config = db_config
        self.verbose = verbose  # If True, print messages to stdout (for Jupyter)


    def _log(self, message, level=logging.INFO):
        """Log a message, and print if verbose is True."""
        if self.verbose:
            print(message)
        if level == logging.ERROR:
            logger.error(message)
        else:
            logger.info(message)


    def test_connection(self):
        """
        Test if a connection to the PostgreSQL database can be established.
        db_config (dict): Database connection parameters (host, port, user, password, database).
        returns: True if the connection is successful, False otherwise.
        """
        try:
            with psycopg2.connect(**self.db_config) as conn:
                self._log("Connection successful!")
                return True
        except OperationalError as e:
            self._log(f"Connection failed: {e}")
            return False
        except DatabaseError as e:
            self._log(f"Database error: {e}")
            return False


    def fetch_site_id_by_prefix(self, prefix):
        """
        Get the site ids from the database
        prefix: text a site prefix, e.g. BBNSF_1205H
        returns: int id of the site, if found
        """
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM sites WHERE prefix LIKE %s;", (f"%{prefix}%",))
                    row = cursor.fetchone()
                    if not row:
                        return None
                    else:
                        return row[0]

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")


    def fetch_label_id_by_species_name(self, species_name):
        """
        Get from the database the labels corresponding to the species
        prefix: text a species name, e.g. Anthus trivialis
        returns: int id of the label, if found
        """
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("select id from labels where name like %s;", (f"%{species_name}%",))
                    row = cursor.fetchone()
                    if not row:
                        return None
                    else:
                        return row[0]

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")


    def fetch_model_id_by_model_name(self, model_name):
        """
        Get from the database the model corresponding to the name
        prefix: text a model name, e.g. BirdNET+_v0.3_global11K_prev3
        returns: int id of the label, if found
        """
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("select id from models where name like %s;", (f"%{model_name}%",))
                    row = cursor.fetchone()
                    if not row:
                        return None
                    else:
                        return row[0]

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")


    def days_between_dates(self, datestr1, datestr2):
        """
        Helper function to count days between dates.
        The start date and the end date are included in the count.
        This method does not query the database. To get the number of dates with a recording, use days_with_recordings instead.

        date1, date2: string in the form YYYY-MM-DD
        return int number of days between dates
        """
        date1 = datetime.strptime(datestr1, '%Y-%m-%d')
        date2 = datetime.strptime(datestr2, '%Y-%m-%d')
        # Calculate the difference
        delta = abs((date2 - date1).days) + 1

        # Get the absolute number of days
        return delta


    def days_with_recordings(self, start_date, end_date, site_id):
        """
        Number of days where a recording was made on this site between these dates.
        The number of days is counted from the recordings in the database, independently of the
        inference parameters (model, species, threshold are NOT considered).

        date1, date2: string in the form YYYY-MM-dd
        site_id: int id in the sites table in the database
        return int days count
        """
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                        select count(distinct date(record_datetime)) from records where
                        site_id=%(site_id)s
                        and record_datetime >= %(start_date)s and record_datetime <= %(end_date)s
                    """
                    params = {
                        "site_id": site_id, "start_date": start_date, "end_date": end_date,
                    }
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    if not row:
                        return None
                    else:
                        return row[0]

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")


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


    def fetch_acoustic_activity_counts(self, species_name, model_name, threshold, site_prefix, start_date, end_date):
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
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                    with record_ids as (
                        select id from records where site_id=%(site_id)s
                        and record_datetime >= %(start_date)s and record_datetime <= %(end_date)s
                    )
                    select count(id) from model_inference_results_max_confidence
                    where
                    confidence >= %(threshold)s and label_id=%(label_id)s
                    and model_id=%(model_id)s
                    and record_id in (select id from record_ids);
                    """
                    params = {
                        "site_id": site_id,
                        "start_date": f"{start_date}T00:00:00+01:00",
                        "end_date": f"{end_date}T23:59:59+01:00",
                        "threshold": threshold, "label_id": label_id, "model_id": model_id
                    }
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    if not row:
                        return None
                    else:
                        return row[0]

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")


    def fetch_count_acoustic_activity_days(self,
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
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                    SELECT COUNT(DISTINCT DATE(r.record_datetime)) AS unique_days_count
                    FROM model_inference_results_pt_record mir
                    JOIN records r ON mir.record_id = r.id
                    WHERE mir.model_id = %(model_id)s
                      AND mir.label_id = %(label_id)s
                      AND r.site_id = %(site_id)s
                      AND mir.confidence >= %(threshold)s
                      AND r.record_datetime >= %(start_date)s and r.record_datetime <= %(end_date)s;
                      """
                    params = {
                        "site_id": site_id,
                        "label_id": label_id,
                        "model_id": model_id,
                        "start_date": f"{start_date}T00:00:00+01:00",
                        "end_date": f"{end_date}T23:59:59+01:00",
                        "threshold": threshold,
                    }
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    if not row:
                        return None
                    else:
                        return row[0]

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")

    def count_species_with_threshold(self, site_prefix, model_name, threshold=0.5):
        """
        Counts the number of species in a site above a threshold.

        site_prefix: prefix in the sites table in the database
        model_name: name of a model as stored in the database
        threshold: float threshold for this species and model
        returns: int
        """
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        model_id = self.fetch_model_id_by_model_name(model_name)
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                    SELECT COUNT(DISTINCT mir.label_id) AS unique_label_count
                    FROM model_inference_results_view mir
                    JOIN records r ON mir.record_id = r.id
                    WHERE r.site_id =  %(site_id)s
                      AND mir.model_id =  %(model_id)s
                      AND mir.confidence >=  %(threshold)s;
                    """
                    params = {
                        "site_id": site_id,
                        "model_id": model_id,
                        "threshold": threshold
                    }
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    if not row:
                        return None
                    else:
                        return row[0]

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")


    def fetch_species_with_threshold(self, site_prefix, model_name, threshold=0.5):
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
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                            SELECT * FROM (
                                SELECT DISTINCT ON (l.id)
                                    s.prefix AS site_prefix,
                                    s.name AS site_name,
                                    r.record_datetime::date AS date,
                                    r.record_datetime::time AS time,
                                    r.filename,
                                    mir.start_time,
                                    mir.end_time,
                                    m.name AS model_name,
                                    l.name AS species,
                                    mir.confidence
                                FROM model_inference_results_view mir
                                JOIN records r ON r.id = mir.record_id
                                JOIN sites  s ON s.id = r.site_id
                                JOIN models m ON m.id = mir.model_id
                                JOIN labels l ON l.id = mir.label_id
                                WHERE r.site_id = %(site_id)s
                                  AND mir.model_id = %(model_id)s
                                  AND mir.confidence >= %(threshold)s
                                ORDER BY l.id, mir.confidence DESC
                            ) t
                            ORDER BY species;
                            """
                    params = {
                        "site_id": site_id,
                        "model_id": model_id,
                        "threshold": threshold
                    }
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    if not rows:
                        return None
                    else:
                        # Get column names from cursor.description
                        column_names = [desc[0] for desc in cursor.description]
                        results = []
                        for row in rows:
                            result = dict()
                            for idx, col_name in enumerate(column_names):
                                result[col_name] = row[idx]
                            results.append(result)
                        return results

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")


    def sites(self):
        """
        Fetches all sites in the database.
        Returns: list of dict
        """
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT
                            sites.prefix, sites.name
                        FROM sites
                        ORDER BY
                            sites.name
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    if not rows:
                        return None
                    else:
                        # Get column names from cursor.description
                        column_names = [desc[0] for desc in cursor.description]
                        results = []
                        for row in rows:
                            result = dict()
                            for idx, col_name in enumerate(column_names):
                                result[col_name] = row[idx]
                            results.append(result)
                        return results

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")

    def sites_years(self):
        """
        Fetches all sites and years combinations in the database.
        Returns: list of dict
        """
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT
                            sites.prefix, sites.name,
                            EXTRACT(YEAR FROM records.record_datetime)::integer AS year,
                            COUNT(*) AS count
                        FROM
                            records
                        JOIN
                            sites ON records.site_id = sites.id
                        GROUP BY
                            sites.prefix, sites.name,
                            EXTRACT(YEAR FROM records.record_datetime)::integer
                        ORDER BY
                            sites.name,
                            year;
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    if not rows:
                        return None
                    else:
                        # Get column names from cursor.description
                        column_names = [desc[0] for desc in cursor.description]
                        results = []
                        for row in rows:
                            result = dict()
                            for idx, col_name in enumerate(column_names):
                                result[col_name] = row[idx]
                            results.append(result)
                        return results

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")


    def fetch_thresholds(self, species_name, model_name):
        """
        Fetches the experimental, preliminary and final threshold
        for this species and model.
        If there are multiple values within a category, return only the latest.
        Returns dict with keys 'experimental', 'preliminary', 'final';
        missing types get None.
        """
        label_id = self.fetch_label_id_by_species_name(species_name)
        model_id = self.fetch_model_id_by_model_name(model_name)
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                    SELECT DISTINCT ON (threshold_type)
                        t.threshold_type,
                        t.threshold
                    FROM thresholds t
                    WHERE t.label_id = %(label_id)s
                      AND t.model_id = %(model_id)s
                      AND t.threshold_type IN ('experimental', 'preliminary', 'final')
                    ORDER BY t.threshold_type, t.set_at DESC;
                    """
                    cursor.execute(query, {"label_id": label_id, "model_id": model_id})
                    return {
                        "experimental": None,
                        "preliminary":  None,
                        "final":        None,
                    } | dict(cursor.fetchall())   # overwrites found types
        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")

    def fetch_inferences(self, species_name, model_name, site_prefix, year, min_confidence=0):
        """
        Fetch all inferences for this combination of species, site and year.
        Returns: list of dict
        """
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        label_id = self.fetch_label_id_by_species_name(species_name)
        model_id = self.fetch_model_id_by_model_name(model_name)
        print(f"Processing: {site_prefix} ({site_id}), {year}, {species_name} ({label_id}), {model_name} ({model_id})")
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                        WITH ids AS (
                            SELECT id
                            FROM records
                            WHERE site_id = %(site_id)s
                            AND EXTRACT(YEAR FROM record_datetime) = %(year)s
                        ),
                        latest_thresholds AS (
                            SELECT
                                label_id,
                                model_id,
                                threshold_type,
                                threshold,
                                set_at,
                                ROW_NUMBER() OVER (
                                    PARTITION BY label_id, model_id, threshold_type
                                    ORDER BY set_at DESC
                                ) AS rn
                            FROM thresholds
                        )
                        SELECT
                            s.prefix AS site_prefix,
                            s.name AS site_name,
                            r.record_datetime::date AS date,
                            r.record_datetime::time AS time,
                            r.filename,
                            mir.start_time,
                            mir.end_time,
                            m.name AS model_name,
                            l.name AS species,
                            mir.confidence,
                            t_experimental.threshold AS experimental_threshold,
                            t_preliminary.threshold AS preliminary_threshold,
                            t_final.threshold AS final_threshold
                        FROM
                            model_inference_results_view mir
                        JOIN
                            records r ON mir.record_id = r.id
                        JOIN
                            sites s ON r.site_id = s.id
                        JOIN
                            models m ON mir.model_id = m.id
                        JOIN
                            labels l ON mir.label_id = l.id
                        LEFT JOIN
                            latest_thresholds t_experimental ON
                                mir.label_id = t_experimental.label_id AND
                                mir.model_id = t_experimental.model_id AND
                                t_experimental.threshold_type = 'experimental' AND
                                t_experimental.rn = 1
                        LEFT JOIN
                            latest_thresholds t_preliminary ON
                                mir.label_id = t_preliminary.label_id AND
                                mir.model_id = t_preliminary.model_id AND
                                t_preliminary.threshold_type = 'preliminary' AND
                                t_preliminary.rn = 1
                        LEFT JOIN
                            latest_thresholds t_final ON
                                mir.label_id = t_final.label_id AND
                                mir.model_id = t_final.model_id AND
                                t_final.threshold_type = 'final' AND
                                t_final.rn = 1
                        WHERE
                            mir.record_id IN (SELECT id FROM ids)
                            AND mir.label_id = %(label_id)s
                            AND mir.model_id = %(model_id)s
                            AND mir.confidence >= %(min_confidence)s;
                    """

                    params = {
                        "site_id": site_id,
                        "year": year,
                        "label_id":label_id,
                        "model_id": model_id,
                        "min_confidence": min_confidence
                    }
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    if not rows:
                        print("Found no results")
                        return None
                    else:
                        # Get column names from cursor.description
                        column_names = [desc[0] for desc in cursor.description]
                        results = []
                        for row in rows:
                            result = dict()
                            for idx, col_name in enumerate(column_names):
                                result[col_name] = row[idx]
                            results.append(result)
                        print("Found %d results" % len(results))
                        return results

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")


    def fetch_max_pro_record(self, species_name, model_name, site_prefix, year, min_confidence=0):
        """
        Fetch all max pro record inferences for this combination of species, site and year.
        Returns: list of dict
        """
        site_id = self.fetch_site_id_by_prefix(site_prefix)
        label_id = self.fetch_label_id_by_species_name(species_name)
        model_id = self.fetch_model_id_by_model_name(model_name)
        print(f"Processing: {site_prefix} ({site_id}), {year}, {species_name} ({label_id}), {model_name} ({model_id})")
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    query = """
                        WITH ids AS (
                            SELECT id
                            FROM records
                            WHERE site_id = %(site_id)s
                            AND EXTRACT(YEAR FROM record_datetime) = %(year)s
                        ),
                        latest_thresholds AS (
                            SELECT
                                label_id,
                                model_id,
                                threshold_type,
                                threshold,
                                set_at,
                                ROW_NUMBER() OVER (
                                    PARTITION BY label_id, model_id, threshold_type
                                    ORDER BY set_at DESC
                                ) AS rn
                            FROM thresholds
                        )
                        SELECT
                            s.prefix AS site_prefix,
                            s.name AS site_name,
                            r.record_datetime::date AS date,
                            r.record_datetime::time AS time,
                            r.filename,
                            maxs.start_time,
                            maxs.end_time,
                            m.name AS model_name,
                            l.name AS species,
                            maxs.confidence,
                            t_experimental.threshold AS experimental_threshold,
                            t_preliminary.threshold AS preliminary_threshold,
                            t_final.threshold AS final_threshold
                        FROM
                            model_inference_results_max_confidence maxs
                        JOIN
                            records r ON maxs.record_id = r.id
                        JOIN
                            sites s ON r.site_id = s.id
                        JOIN
                            models m ON maxs.model_id = m.id
                        JOIN
                            labels l ON maxs.label_id = l.id
                        LEFT JOIN
                            latest_thresholds t_experimental ON
                                maxs.label_id = t_experimental.label_id AND
                                maxs.model_id = t_experimental.model_id AND
                                t_experimental.threshold_type = 'experimental' AND
                                t_experimental.rn = 1
                        LEFT JOIN
                            latest_thresholds t_preliminary ON
                                maxs.label_id = t_preliminary.label_id AND
                                maxs.model_id = t_preliminary.model_id AND
                                t_preliminary.threshold_type = 'preliminary' AND
                                t_preliminary.rn = 1
                        LEFT JOIN
                            latest_thresholds t_final ON
                                maxs.label_id = t_final.label_id AND
                                maxs.model_id = t_final.model_id AND
                                t_final.threshold_type = 'final' AND
                                t_final.rn = 1
                        WHERE
                            maxs.record_id IN (SELECT id FROM ids)
                            AND maxs.label_id = %(label_id)s
                            AND maxs.model_id = %(model_id)s
                            AND maxs.confidence >= %(min_confidence)s;
                    """

                    params = {
                        "site_id": site_id,
                        "year": year,
                        "label_id":label_id,
                        "model_id": model_id,
                        "min_confidence": min_confidence
                    }
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    if not rows:
                        print("Found no results")
                        return None
                    else:
                        # Get column names from cursor.description
                        column_names = [desc[0] for desc in cursor.description]
                        results = []
                        for row in rows:
                            result = dict()
                            for idx, col_name in enumerate(column_names):
                                result[col_name] = row[idx]
                            results.append(result)
                        print("Found %d results" % len(results))
                        return results

        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")
