import time
import json
from kafka import KafkaProducer
from datetime import datetime, timedelta
import random

# --- CONFIGURACIÓN ---
# El BROKER se refiere al nombre del host del servicio Kafka dentro de la red Docker Compose.
# En el docker-compose.yml, el host es 'kafka-broker'
BOOTSTRAP_SERVERS = ['kafka-broker:9092'] 
TOPIC_NAME = 'user_activity'

# El gap de inactividad de la ventana de sesión en Flink es de 5 segundos (5000 ms).
# Usaremos 6 segundos para garantizar que la ventana se cierre.
SESSION_GAP_SECONDS = 6

# --- DATOS SIMULADOS ---
# Simulación de dos usuarios con un patrón de sesión
# La hora de inicio para simular los timestamps
START_TIME = datetime.now() 

# Escenario: Dos sesiones para user_A
# La Ventana de Sesión de 5s debe cerrarse entre la Sesión 1 y la Sesión 2.
EVENTS = [
    # SESIÓN 1 (user_A y user_B están activos)
    {'user_id': 'user_A', 'page': '/login', 'delay': 0, 'time_offset': 1}, 
    {'user_id': 'user_B', 'page': '/product/1', 'delay': 0.5, 'time_offset': 2},
    {'user_id': 'user_A', 'page': '/checkout', 'delay': 0.5, 'time_offset': 3}, 
    
    # PAUSA: 7 SEGUNDOS para forzar el cierre de la Ventana de Sesión de 5s
    # Flink verá una Watermark que supera el final de la ventana de la Sesión 1.
    {'user_id': 'user_A', 'page': '/homepage', 'delay': SESSION_GAP_SECONDS + 1, 'time_offset': 10}, 
    
    # SESIÓN 2 (user_A inicia una nueva sesión)
    {'user_id': 'user_B', 'page': '/logout', 'delay': 0.5, 'time_offset': 11},
    {'user_id': 'user_A', 'page': '/settings', 'delay': 1, 'time_offset': 12}, 
]

def generate_events():
    """Genera eventos con timestamps basados en el tiempo de inicio."""
    
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=str.encode # Serializa el valor como string simple
    )

    print(f"--- Iniciando Productor de Kafka: {TOPIC_NAME} ---")
    print(f"La Ventana de Sesión (Gap) a probar es de {SESSION_GAP_SECONDS} segundos.")

    current_simulated_time = START_TIME
    
    for event in EVENTS:
        # Espera el tiempo de retraso (simula el intervalo entre eventos)
        time.sleep(event['delay']) 
        
        # Simula el Event Time real (la marca de tiempo en el dato)
        # Añade el offset de tiempo para simular Event Time desordenado si fuera necesario
        event_time_ms = int((START_TIME + timedelta(seconds=event['time_offset'])).timestamp() * 1000)

        # Formato del mensaje: USER_ID,TIMESTAMP_MS,PAGE
        message = f"{event['user_id']},{event_time_ms},{event['page']}"
        
        # Enviar mensaje
        producer.send(
            TOPIC_NAME, 
            value=message,
            key=event['user_id'].encode('utf-8') # Usar el ID de usuario como clave de partición de Kafka
        )
        
        print(f"ENVIADO (Event Time: {event['time_offset']}s): {message}")
        
    producer.flush()
    print("\n--- Producción de Eventos Finalizada ---")

if __name__ == "__main__":
    # Espera un momento para asegurar que Kafka esté completamente levantado
    time.sleep(5) 
    generate_events()