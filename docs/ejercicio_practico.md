# Laboratorio: Análisis de Sesiones de Usuario (Kafka -> Flink -> PostgreSQL)

## 🎯 Objetivo del Ejercicio (Capítulo 4.5)

El objetivo de este laboratorio es implementar un pipeline de streaming con estado que resuelva dos desafíos clave de la ingeniería de datos: la corrección temporal (usando Ventanas de Sesión) y la consistencia en el destino (usando idempotencia en PostgreSQL).

El Job debe calcular la duración de la sesión y el total de eventos por usuario, persistiendo el resultado en la base de datos.

## 🛠️ Entorno de Práctica (Docker)

El laboratorio se ejecuta sobre un entorno multi-contenedor:

| Servicio | Rol en Flink | URL de Conexión | 
 | ----- | ----- | ----- | 
| **Kafka** | Fuente de Eventos (Source) | kafka:9092 | 
| **Flink** | Motor de Procesamiento | N/A (Se ejecuta el Job) | 
| **PostgreSQL** | Destino de Datos (Sink) | jdbc:postgresql://postgres:5432/flink_db | 

### Esquema del Destino (Tabla aggregated_counts)

La tabla de PostgreSQL ya está creada y tiene la siguiente estructura:

CREATE TABLE IF NOT EXISTS aggregated_counts (
group_key VARCHAR(255) PRIMARY KEY, -- Clave de la sesión para UPSERT
count_value BIGINT,                 -- Total de eventos en esa sesión
window_end_time TIMESTAMP           -- Hora de cierre de la ventana
);

## 📝 Enunciado y Requisitos Técnicos

Desarrolle el Job de Flink (SessionWindowJob.java) que implemente la siguiente lógica:

1. **Fuente de Datos:** Leer del Topic de Kafka (user_activity).

2. **Modo de Tiempo:** Configurar el entorno para usar Event Time.

3. **Partición:** Utilizar keyBy() sobre el User ID para garantizar que los eventos del mismo usuario se procesen juntos.

4. **Ventanas:** Agrupar los eventos con una Ventana de Sesión (SessionWindow) con un gap de inactividad de 5 segundos.

5. **Cálculo:** Dentro de la ventana, contar el número total de eventos (count_value) por cada sesión de usuario.

6. **Consistencia del Sink:** Utilizar la lógica ON CONFLICT en el JdbcSink para garantizar que si el Job se reinicia y reenvía un resultado, este se actualice y no cree duplicados (Patrón At Least Once + Idempotencia).

## 🚀 Paso a Paso para la Prueba (Simulación Manual)

Para probar la Ventana de Sesión de 5 segundos, debe ingresar eventos con un patrón de pausas:

1. **Crear Topic** (Si no existe, ejecutar en el contenedor de Kafka):

   kafka-topics --create --topic user_activity --bootstrap-server kafka:9092

2. **Simular Actividad (Patrón de Sesión):**

   * Ingresar el **Primer Evento (user_A)**: Esto abre la sesión.

     user_A,1000

   * Ingresar **Segundo Evento (user_A)**, poco después: Esto mantiene la sesión **abierta**.

     user_A,2000

   * **Esperar 6 Segundos:** (Más que el gap de 5s).

   * Ingresar el **Tercer Evento (user_A)**: Esto **cierra la sesión anterior** y **abre una nueva sesión**.

Al consultar la tabla aggregated_counts después de que la segunda sesión se cierre (por la Watermark), deberían verse **dos registros** para user_A.