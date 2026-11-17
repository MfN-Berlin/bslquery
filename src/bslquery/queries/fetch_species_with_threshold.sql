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
