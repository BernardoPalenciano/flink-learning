-- Se recomienda usar IF NOT EXISTS para que el script no falle si se ejecuta varias veces.
CREATE TABLE IF NOT EXISTS aggregated_counts (
    group_key VARCHAR(255) PRIMARY KEY, -- Usamos PRIMARY KEY si el campo es único (ej. para actualizaciones)
    count_value BIGINT,
    window_end_time TIMESTAMP
);