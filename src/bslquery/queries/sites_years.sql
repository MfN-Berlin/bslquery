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
