-- Se recomienda usar IF NOT EXISTS para que el script no falle si se ejecuta varias veces.
CREATE TABLE IF NOT EXISTS session_results (
    user_id VARCHAR(255) PRIMARY KEY, -- Usamos PRIMARY KEY si el campo es único (ej. para actualizaciones)
    total_clicks BIGINT,
    session_start_time TIMESTAMP
);