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
import sys


load_dotenv()

app = Flask(__name__)

# Configure Logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ])

# MongoDB Configuration
def setup_mongo():
    logging.info("Setting up MongoDB...")
    MONGO_URI = os.getenv("MONGO_URI")
    client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    db = client["skibims_db"]
    collection = db["sensor_data"]
    logging.info("MongoDB setup complete")
    return collection


collection = setup_mongo()

# MQTT Configuration
MQTT_BROKER = "broker.emqx.io"
MQTT_TOPIC = "/UNI169/skibims/sensor"


def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when connected to MQTT broker"""
    if reason_code == 0:
        logging.info("Connected to MQTT broker successfully")
        client.subscribe(MQTT_TOPIC)
    else:
        logging.error(f"Failed to connect, return code {reason_code}")


def on_subscribe(client, userdata, mid, reason_code_list, properties):
    logging.info(f"Subscribed to topic: {MQTT_TOPIC}")


def on_message(client, userdata, msg):
    """Callback when a message is received from MQTT"""
    try:
        payload = json.loads(msg.payload.decode())
        logging.info(f"Received payload: {payload}")

        # Validate required fields
        required_fields = {"device_id", "type"}
        if not all(field in payload for field in required_fields):
            logging.warning(f"Invalid message structure: {payload}")
            return

        # Add timestamp
        payload["timestamp"] = datetime.now()

        # Store in MongoDB
        collection.insert_one(payload)
        logging.info(f"Data stored successfully: {payload}")

    except Exception as e:
        logging.error(f"Error processing message: {e}")


def run_mqtt():
    """Run MQTT client in a separate thread"""
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_subscribe = on_subscribe
    mqtt_client.on_message = on_message
    logging.info("Connecting to MQTT broker...")
    mqtt_client.connect(MQTT_BROKER)
    logging.info("Listening for messages...")
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
    app.run(debug=True, use_reloader=False)
