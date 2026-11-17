SELECT COUNT(DISTINCT mir.label_id) AS unique_label_count
FROM model_inference_results_view mir
JOIN records r ON mir.record_id = r.id
WHERE r.site_id =  %(site_id)s
  AND mir.model_id =  %(model_id)s
  AND mir.confidence >=  %(threshold)s;
