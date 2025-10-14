# Proyecto de Procesamiento de Streams con Apache Flink

Este repositorio contiene un proyecto de ejemplo para practicar el desarrollo de un pipeline de streaming de datos en tiempo real. La arquitectura utiliza **Apache Kafka** como fuente (Source) y **PostgreSQL** como destino (Sink), con **Apache Flink** realizando la transformación de datos.

## 🚀 Arquitectura del Proyecto

El entorno se orquesta completamente con Docker Compose y consta de cuatro servicios principales:

| Servicio | Componente | Hostname Interno | Puerto Externo |
| :--- | :--- | :--- | :--- |
| `broker` | Apache Kafka (Modo KRaft) | `kafka-broker` | `9092` |
| `jobmanager` | Apache Flink Job Manager | `flink-jobmanager` | `8081` |
| `taskmanager` | Apache Flink Task Manager | `flink-taskmanager` | N/A |
| `postgres` | PostgreSQL (Base de Datos Sink) | `flink-postgres` | `5432` |

---

## 🛠️ Requisitos Previos

Asegúrate de tener instalado y configurado lo siguiente en tu sistema (Windows):

1.  **Docker Desktop:** Para ejecutar Docker Compose.
2.  **Java/JDK:** Para compilar el código de Flink (generalmente Java 11 o superior).
3.  **Maven o Gradle:** Para gestionar las dependencias y compilar el proyecto.
4.  **Python 3.x:** Necesario para ejecutar los scripts de utilidad (productores de datos).
    * **Dependencia Python:** Instala la librería `kafka-python`: `pip install kafka-python` (Necesaria solo si se usa el script productor de datos desde el host).

---

## 🏁 Pasos para Arrancar el Proyecto

Sigue estos pasos en orden para poner en marcha el entorno y el Job de Flink:

### Paso 1: Iniciar y Construir la Infraestructura de Docker

Dado que el contenedor de Kafka necesita Python para ejecutar los scripts de utilidad, la imagen debe ser **construida**.

Navega hasta el directorio **`infra/`** (donde se encuentra `docker-compose.yml`) y levanta todos los servicios.

```bash
# Navegar al directorio donde se encuentra el docker-compose.yml
cd infra

# Construir las imágenes custom y levantar todos los contenedores en modo detached (-d)
# Esto crea una imagen de Kafka con Python y la librería 'kafka-python'.
docker compose up -d --build

### Paso 2: Configuración de Source y Sink (Creación de Topic y Tabla)
Una vez que los contenedores estén operativos, usa la CLI de Docker para ejecutar los comandos dentro de los contenedores.

A. Crear el Topic de Kafka (input-clicks)
El script create_topic.py se ejecuta dentro del contenedor kafka-broker. Esto garantiza que la conexión use el nombre interno (kafka-broker:9092) de manera fiable.

Comando de Ejecución (desde el directorio infra/):

Bash
# El script está montado en la ruta /scripts dentro del contenedor
docker exec kafka-broker python3 /scripts/create-topic.py
Verificación:
El script esperará 20 segundos y si es exitoso, mostrará: ✅ Topic 'input-clicks' creado con éxito.

B. Creación de la Tabla de PostgreSQL (aggregated_counts)
La tabla de destino de Flink se crea automáticamente al inicio del servicio de la base de datos, mapeando el archivo create_table.sql en el docker-compose.yml. -> esto no he conseguido que funcione por lo que hay que crear la tabla manualmente
Bash
# Entramos en el docker de postgres-db
 docker exec -it postgres-db psql -U user -d flinkdb
# Ejecutamos el sql
CREATE TABLE IF NOT EXISTS aggregated_counts (
    group_key VARCHAR(255) PRIMARY KEY, 
    count_value BIGINT,
    window_end_time TIMESTAMP
);
