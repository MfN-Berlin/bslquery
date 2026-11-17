import functools

from psycopg2 import OperationalError, DatabaseError


def db_query(func):
    """Open connection+cursor, inject the cursor, turn psycopg2 errors into logged None."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    return func(self, cursor, *args, **kwargs)
        except OperationalError as e:
            self._log(f"Connection failed: {e}")
        except DatabaseError as e:
            self._log(f"Query failed: {e}")
    return wrapper

def rows_as_dicts(cursor):
    rows = cursor.fetchall()
    if not rows:
        return None                      # tests assert empty result -> None
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in rows]