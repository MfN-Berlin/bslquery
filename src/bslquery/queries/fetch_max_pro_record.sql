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
