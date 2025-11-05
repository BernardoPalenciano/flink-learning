-- Se recomienda usar IF NOT EXISTS para que el script no falle si se ejecuta varias veces.
CREATE TABLE IF NOT EXISTS session_results (
    user_id VARCHAR(255) NOT NULL,
    total_clicks BIGINT,
    session_start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    -- CLAVE PRIMARIA COMPUESTA: Es única por usuario Y por hora de inicio de sesión
    PRIMARY KEY (user_id, session_start_time) 
);