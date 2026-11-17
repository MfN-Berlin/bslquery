select count(distinct date(record_datetime)) from records where
site_id=%(site_id)s
and record_datetime >= %(start_date)s and record_datetime <= %(end_date)s
