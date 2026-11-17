"""SQL for bslquery: one .sql file per BioSoundsLabDB query method.

Files are loaded as package resources so they work from the source tree
and from an installed wheel alike. Constant names match the method names
in upper case, e.g. SITES is used by BioSoundsLabDB.sites().
"""

from importlib.resources import files


def load(name: str) -> str:
    """Read queries/<name>.sql and return it as a string."""
    return files("bslquery.queries").joinpath(f"{name}.sql").read_text()


FETCH_SITE_ID_BY_PREFIX = load("fetch_site_id_by_prefix")
FETCH_LABEL_ID_BY_SPECIES_NAME = load("fetch_label_id_by_species_name")
FETCH_MODEL_ID_BY_MODEL_NAME = load("fetch_model_id_by_model_name")
DAYS_WITH_RECORDINGS = load("days_with_recordings")
FETCH_ACOUSTIC_ACTIVITY_COUNTS = load("fetch_acoustic_activity_counts")
FETCH_COUNT_ACOUSTIC_ACTIVITY_DAYS = load("fetch_count_acoustic_activity_days")
COUNT_SPECIES_WITH_THRESHOLD = load("count_species_with_threshold")
FETCH_SPECIES_WITH_THRESHOLD = load("fetch_species_with_threshold")
SITES = load("sites")
SITES_YEARS = load("sites_years")
FETCH_THRESHOLDS = load("fetch_thresholds")
FETCH_INFERENCES = load("fetch_inferences")
FETCH_MAX_PRO_RECORD = load("fetch_max_pro_record")
