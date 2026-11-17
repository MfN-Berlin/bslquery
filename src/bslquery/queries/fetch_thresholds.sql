SELECT DISTINCT ON (threshold_type)
    t.threshold_type,
    t.threshold
FROM thresholds t
WHERE t.label_id = %(label_id)s
  AND t.model_id = %(model_id)s
  AND t.threshold_type IN ('experimental', 'preliminary', 'final')
ORDER BY t.threshold_type, t.set_at DESC;
