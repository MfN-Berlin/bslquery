with record_ids as (
    select id from records where site_id=%(site_id)s
    and record_datetime >= %(start_date)s and record_datetime <= %(end_date)s
)
select count(id) from model_inference_results_max_confidence
where
confidence >= %(threshold)s and label_id=%(label_id)s
and model_id=%(model_id)s
and record_id in (select id from record_ids);
