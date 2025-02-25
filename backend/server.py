from flask import Flask, jsonify, request
import paho.mqtt.client as mqtt
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import json
import threading
import os
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
db = client["skibims_db"]
collection = db["sensor_data"]

# MQTT Configuration
# Change to your broker address
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.emqx.io")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8084))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "/UNI169/skibims/sensor")

print("MQTT Broker:", MQTT_BROKER)
print("MQTT Port:", MQTT_PORT)

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    logger.debug(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    """Callback when a message is received from MQTT"""
    logger.debug(f"Message received on topic {msg.topic}: {msg.payload}")

    try:
        payload = json.loads(msg.payload.decode())
        logger.debug(f"Decoded payload: {payload}")

        # Validate required fields
        required_fields = {"device_id", "temp", "humidity", "light", "type"}
        if not all(field in payload for field in required_fields):
            logger.warning(f"Invalid message structure: {payload}")
            return

        # Add timestamp
        payload["timestamp"] = datetime.utcnow()

        # Store in MongoDB
        collection.insert_one(payload)
        logger.info(f"Data stored successfully: {payload}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")


# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


def run_mqtt():
    """Run MQTT client in a separate thread"""
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()


# Start MQTT listener in a background thread
threading.Thread(target=run_mqtt, daemon=True).start()


@app.route("/api/sensor", methods=["GET"])
def get_sensor_data():
    """Fetch sensor data from MongoDB with optional time filters"""
    from_time = request.args.get("from")
    to_time = request.args.get("to")

    query = {}
    if from_time or to_time:
        query["timestamp"] = {}
        if from_time:
            query["timestamp"]["$gte"] = datetime.fromisoformat(from_time)
        if to_time:
            query["timestamp"]["$lte"] = datetime.fromisoformat(to_time)

    data = list(collection.find(query, {"_id": 0}))
    return jsonify(data), 200


if __name__ == "__main__":
    # Disable reloader to prevent duplicate MQTT connections
    app.run(use_reloader=False)
