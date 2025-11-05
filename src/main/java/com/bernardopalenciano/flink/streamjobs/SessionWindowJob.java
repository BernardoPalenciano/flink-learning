package com.bernardopalenciano.flink.streamjobs;

import org.apache.flink.api.common.eventtime.SerializableTimestampAssigner;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.reader.deserializer.KafkaRecordDeserializationSchema;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.EventTimeSessionWindows;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;
import org.apache.flink.connector.jdbc.JdbcSink;
import org.apache.flink.connector.jdbc.JdbcConnectionOptions;
import org.apache.flink.connector.jdbc.JdbcExecutionOptions;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.api.common.typeinfo.Types;

import java.sql.Timestamp;
import java.time.Duration;

/**
 * Job de Flink para calcular el total de clics por usuario dentro de una Ventana de Sesión.
 *
 * Configuración:
 * 1. Lee datos de Kafka (topic 'user_activity').
 * 2. Asigna Event Time y Watermarks.
 * 3. Aplica Ventanas de Sesión con un gap de inactividad de 5 segundos.
 * 4. Persiste el resultado (Usuario, Conteo, Inicio de Sesión) en PostgreSQL.
 */
public class SessionWindowJob {

    // ---------------------- 1. POJOS (Plain Old Java Objects) ----------------------

    /**
     * POJO de Entrada: Representa un evento de actividad de usuario de Kafka.
     * Formato esperado: userId, timestamp, url
     */
    public static class UserActivityEvent {
        public String userId;
        public long timestamp; // Timestamp del evento en milisegundos
        public String url;

        // Constructor sin argumentos necesario para la deserialización de Flink
        public UserActivityEvent() {}

        public UserActivityEvent(String userId, long timestamp, String url) {
            this.userId = userId;
            this.timestamp = timestamp;
            this.url = url;
        }

        @Override
        public String toString() {
            return "UserActivityEvent{" + "userId='" + userId + '\'' + ", timestamp=" + timestamp + ", url='" + url + '\'' + '}';
        }
    }

    /**
     * POJO de Salida: Representa el resultado de la ventana de sesión.
     * Almacena el ID de usuario, el conteo de clics y el inicio de la ventana (sesión).
     */
    public static class SessionResult {
        public String userId;
        public long totalClicks;
        public Timestamp sessionStartTime; // Tiempo de inicio de la ventana (sesión)

        // Constructor sin argumentos
        public SessionResult() {}

        public SessionResult(String userId, long totalClicks, long sessionStartTime) {
            this.userId = userId;
            this.totalClicks = totalClicks;
            this.sessionStartTime = new Timestamp(sessionStartTime);
        }

        @Override
        public String toString() {
            return "SessionResult{" + "userId='" + userId + '\'' + ", totalClicks=" + totalClicks + ", sessionStartTime=" + sessionStartTime + '}';
        }
    }

    // ---------------------- 2. JOB PRINCIPAL ----------------------

    public static void main(String[] args) throws Exception {
        // Entorno de ejecución de Flink
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        // Configuración para usar Event Time
        env.setParallelism(1); // Paralelismo a 1 para hacer la prueba más predecible

        // 1. Configuración del Kafka Source
        KafkaSource<UserActivityEvent> kafkaSource = KafkaSource.<UserActivityEvent>builder()
                .setBootstrapServers("kafka-broker:9092") // Usamos el nombre del servicio Docker
                .setTopics("user_activity")
                .setGroupId("flink-session-group")
                .setStartingOffsets(org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer.earliest())
                // Deserializador: Pasamos la instancia de la clase, ya que implementa KafkaRecordDeserializationSchema
                .setDeserializer(new UserActivityDeserializer())
                .build();

        // 2. Leer de Kafka y aplicar Watermarks (Marca de Agua)
        DataStream<UserActivityEvent> userActivityStream = env.fromSource(kafkaSource,
                WatermarkStrategy
                        // WatermarkStrategy para Event Time. Tolera 5 segundos de latencia (opcional, pero buena práctica).
                        .<UserActivityEvent>forBoundedOutOfOrderness(Duration.ofSeconds(5))
                        .withTimestampAssigner((SerializableTimestampAssigner<UserActivityEvent>)
                                (event, recordTimestamp) -> event.timestamp)
                        .withIdleness(Duration.ofSeconds(10)), // Timeout para particiones inactivas (opcional)
                "Kafka Source");


        // 3. Procesamiento: KeyBy, Window y ProcessFunction
        DataStream<SessionResult> sessionResults = userActivityStream
                // Agrupamos por ID de usuario (clave de la ventana)
                .keyBy(event -> event.userId)
                // Aplicamos la Ventana de Sesión con un gap de inactividad de 5 segundos
                .window(EventTimeSessionWindows.withGap(Duration.ofSeconds(5)))
                // Dentro de cada ventana, contamos los eventos
                .process(new org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction<UserActivityEvent, SessionResult, String, TimeWindow>() {
                    @Override
                    public void process(String key, Context context, Iterable<UserActivityEvent> elements, Collector<SessionResult> out) throws Exception {
                        long count = 0;
                        for (UserActivityEvent element : elements) {
                            count++;
                        }
                        // Emitimos el resultado: ID, Conteo y el Inicio de la Ventana (Session Start Time)
                        out.collect(new SessionResult(key, count, context.window().getStart()));
                    }
                })
                .name("Session Window Counter");

        // Imprimir resultados en consola (opcional)
        sessionResults.print();

        // 4. Sink a PostgreSQL (CORREGIDO: Usamos addSink() en lugar de sinkTo())
        sessionResults.addSink(
                JdbcSink.sink(
                        "INSERT INTO session_results (user_id, total_clicks, session_start_time) VALUES (?, ?, ?)",
                        
                        // PreparedStatement setter
                        (statement, result) -> {
                            statement.setString(1, result.userId);
                            statement.setLong(2, result.totalClicks);
                            statement.setTimestamp(3, result.sessionStartTime);
                        },
                        
                        // Opciones de ejecución (opcional pero recomendado)
                        JdbcExecutionOptions.builder()
                                .withBatchSize(100)
                                .withBatchIntervalMs(200)
                                .withMaxRetries(5)
                                .build(),
                        
                        // Configuración de la conexión
                        new JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                                .withUrl("jdbc:postgresql://postgres-db:5432/flinkdb") // Nombre del servicio Docker de Postgres
                                .withDriverName("org.postgresql.Driver")
                                .withUsername("user") // Usar 'user' según tu docker-compose
                                .withPassword("password") // Usar 'password' según tu docker-compose
                                .build()
                )
        ).name("PostgreSQL Sink");


        // Ejecutar el Job de Flink
        env.execute("Flink Session Window Job");
    }

    /**
     * Deserializador personalizado para convertir la línea CSV de Kafka a UserActivityEvent POJO.
     * Implementa la interfaz moderna KafkaRecordDeserializationSchema.
     * Ejemplo de entrada: "user_A,1678886401000,/login"
     */
    public static class UserActivityDeserializer implements KafkaRecordDeserializationSchema<UserActivityEvent> {

        // Implementación principal para KafkaRecordDeserializationSchema
        @Override
        public void deserialize(ConsumerRecord<byte[], byte[]> record, Collector<UserActivityEvent> out) {
            try {
                // El valor está en el cuerpo del mensaje (record.value())
                String line = new String(record.value());
                String[] parts = line.split(",");

                if (parts.length == 3) {
                    String userId = parts[0].trim();
                    // Conversión a Long para el Event Time
                    long timestamp = Long.parseLong(parts[1].trim());
                    String url = parts[2].trim();

                    out.collect(new UserActivityEvent(userId, timestamp, url));
                } else {
                    // Manejo básico de registros malformados
                    System.err.println("Skipping malformed record: " + line);
                }
            } catch (Exception e) {
                // El bloque catch captura cualquier error de parsing o conversión
                System.err.println("Error deserializing record: " + e.getMessage());
            }
        }

        // Método que indica el tipo de salida, obligatorio en Flink 1.18+
        @Override
        public TypeInformation<UserActivityEvent> getProducedType() {
            return Types.POJO(UserActivityEvent.class);
        }
    }
}