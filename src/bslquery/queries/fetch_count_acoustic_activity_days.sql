SELECT COUNT(DISTINCT DATE(r.record_datetime)) AS unique_days_count
FROM model_inference_results_pt_record mir
JOIN records r ON mir.record_id = r.id
WHERE mir.model_id = %(model_id)s
  AND mir.label_id = %(label_id)s
  AND r.site_id = %(site_id)s
  AND mir.confidence >= %(threshold)s
  AND r.record_datetime >= %(start_date)s and r.record_datetime <= %(end_date)s;
