# Contenido de infra/scripts/create_topic.py

import time
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

# NOTA: Debes usar 'kafka-broker:9092' ya que este script se ejecuta FUERA de Docker, 
# pero la dirección es resuelta por Docker Compose a través de los puertos mapeados o la red de Docker.
BOOTSTRAP_SERVER = 'localhost:9092' # O usa 'kafka-broker:9092' si ejecutas el script DENTRO de un contenedor de Python
TOPIC_NAME = 'input-clicks'
PARTITIONS = 3
REPLICATION_FACTOR = 1

def create_kafka_topic():
    print("Intentando conectar con Kafka...")
    time.sleep(20) # Damos tiempo al broker para arrancar

    try:
        # Usamos KafkaAdminClient para interactuar con el clúster
        admin_client = KafkaAdminClient(bootstrap_servers=BOOTSTRAP_SERVER)
        
        # Define el nuevo topic
        topic_list = [NewTopic(
            name=TOPIC_NAME, 
            num_partitions=PARTITIONS, 
            replication_factor=REPLICATION_FACTOR
        )]
        
        # Crea el topic
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
        print(f"✅ Topic '{TOPIC_NAME}' creado con éxito.")
        
    except TopicAlreadyExistsError:
        print(f"⚠️ El topic '{TOPIC_NAME}' ya existe. Continuamos...")
    except Exception as e:
        print(f"❌ Error al crear el topic: {e}")

if __name__ == "__main__":
    create_kafka_topic()