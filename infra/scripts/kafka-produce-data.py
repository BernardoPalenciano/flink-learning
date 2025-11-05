import time
import json
from kafka import KafkaProducer
from datetime import datetime, timedelta
import random

# --- CONFIGURACIÓN ---
BOOTSTRAP_SERVERS = ['kafka-broker:9092'] 
TOPIC_NAME = 'user_activity'

# Gap de inactividad de la ventana de sesión en Flink: 5 segundos
SESSION_GAP_SECONDS = 6

# --- DATOS SIMULADOS ---
# IMPORTANTE: Generamos timestamps JUSTO ANTES de enviar cada evento
# para que sean "recientes" cuando Flink los procese

EVENTS = [
    # SESIÓN 1 (user_A y user_B están activos)
    {'user_id': 'user_A', 'page': '/login', 'delay': 0, 'time_offset': 0}, 
    {'user_id': 'user_B', 'page': '/product/1', 'delay': 1, 'time_offset': 1},
    {'user_id': 'user_A', 'page': '/checkout', 'delay': 1, 'time_offset': 2}, 
    
    # PAUSA: 7 SEGUNDOS para forzar el cierre de la Ventana de Sesión de 5s
    {'user_id': 'user_A', 'page': '/homepage', 'delay': SESSION_GAP_SECONDS + 1, 'time_offset': SESSION_GAP_SECONDS + 1 + 2}, 
    
    # SESIÓN 2 (user_A inicia una nueva sesión)
    {'user_id': 'user_B', 'page': '/logout', 'delay': 1, 'time_offset': SESSION_GAP_SECONDS + 2 + 2},
    {'user_id': 'user_A', 'page': '/settings', 'delay': 1, 'time_offset': SESSION_GAP_SECONDS + 3 + 2}, 
]

def generate_events():
    """Genera eventos con timestamps ACTUALES basados en el momento de envío."""
    
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=str.encode
    )

    print(f"--- Iniciando Productor de Kafka: {TOPIC_NAME} ---")
    print(f"La Ventana de Sesión (Gap) a probar es de {SESSION_GAP_SECONDS} segundos.")
    print(f"Esperando que Flink esté listo y leyendo...\n")
    
    # CRÍTICO: Capturamos el tiempo de INICIO justo antes de enviar
    start_time = datetime.now()
    
    for i, event in enumerate(EVENTS):
        # Espera el tiempo de retraso antes de enviar este evento
        if i > 0:  # No hay delay para el primer evento
            time.sleep(event['delay'])
        
        # SOLUCIÓN: Calculamos el timestamp basado en el momento ACTUAL
        # No usamos time_offset fijo, sino tiempo transcurrido real
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        event_time_ms = int((start_time + timedelta(seconds=elapsed_seconds)).timestamp() * 1000)

        # Formato del mensaje: USER_ID,TIMESTAMP_MS,PAGE
        message = f"{event['user_id']},{event_time_ms},{event['page']}"
        
        # Enviar mensaje
        producer.send(
            TOPIC_NAME, 
            value=message,
            key=event['user_id'].encode('utf-8')
        )
        
        event_datetime = datetime.fromtimestamp(event_time_ms / 1000)
        print(f"ENVIADO #{i+1} (Timestamp: {event_time_ms}, {event_datetime.strftime('%H:%M:%S')}): {message}")
        
    producer.flush()
    producer.close()
    print("\n--- Producción de Eventos Finalizada ---")
    print("IMPORTANTE: Los eventos fueron enviados con timestamps RECIENTES.")
    print("Flink debería procesarlos y escribirlos en PostgreSQL después del idleness timeout (10s).")

if __name__ == "__main__":
    print("Esperando 5 segundos para que Kafka esté listo...")
    time.sleep(5)
    
    print("\n⚠️  IMPORTANTE: Asegúrate de que el job de Flink YA ESTÉ EJECUTÁNDOSE")
    print("antes de ejecutar este script, o ejecuta este script DESPUÉS de iniciar Flink.\n")
    
    generate_events()
    
    print("\n✅ Eventos enviados. Espera ~15-20 segundos para ver resultados en PostgreSQL.")
    print("Comando para verificar: docker exec -it postgres-db psql -U user -d flinkdb -c 'SELECT * FROM session_results;'")