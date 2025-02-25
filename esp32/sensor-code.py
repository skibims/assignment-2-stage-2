from machine import Pin, ADC
from umqtt.simple import MQTTClient
import ujson
import network
import utime as time
import dht
import urequests as requests

# MQTT Broker configuration
MQTT_CLIENT_ID = "skibims"
MQTT_BROKER = "broker.emqx.io"
MQTT_TOPIC = "/UNI169/skibims/sensor"

# WiFi Configuration
# WIFI_SSID = "POCO F4"
# WIFI_PASSWORD = "CharZaku"
WIFI_SSID = "Illosa"
WIFI_PASSWORD = "octo1703"

# Ubidots Configuration
DEVICE_ID = "esp32-sic6"
TOKEN = "BBUS-tMi16kPrI16pVtswdckwitYhXZwAls"

# Pin Configuration
DHT_PIN = Pin(15)
ldr = ADC(Pin(32))
ldr.atten(ADC.ATTN_11DB)


def mqtt_connect():
    '''Connect to MQTT broker'''
    print("Connecting to MQTT broker ...", end="")
    mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, user="", password="")
    mqtt_client.connect()
    print("Connected.")
    return mqtt_client


def mqtt_client_publish(client, topic, data):
    data['device_id'] = DEVICE_ID
    data['type'] = "sensor"
    print("Publishing to MQTT Broker...")
    print("MQTT payload:", data)
    client.publish(topic, ujson.dumps(data))


def pack_sensor_data(temperature, humidity, light):
    '''Pack sensor data into a dictionary'''
    data = {
        "temp": temperature,
        "humidity": humidity,
        "ldr_value": light,
    }
    return data


def send_data(payload: dict):
    url = "http://industrial.api.ubidots.com/api/v1.6/devices/" + DEVICE_ID
    headers = {"Content-Type": "application/json", "X-Auth-Token": TOKEN}
    print("Ubidots payload:", payload)
    response = requests.post(url, json=payload, headers=headers)
    print("Response:", response.text)


def connect_wifi():
    '''Connect to WiFi'''
    wifi_client = network.WLAN(network.STA_IF)
    wifi_client.active(True)
    print("Connecting device to WiFi")
    wifi_client.connect(WIFI_SSID, WIFI_PASSWORD)

    while not wifi_client.isconnected():
        print("Connecting")
        time.sleep(0.1)
    print("WiFi Connected!")
    print(wifi_client.ifconfig())


def main():
    connect_wifi()

    mqtt_client = mqtt_connect()
    dht_sensor = dht.DHT11(DHT_PIN)
    light = ""
    telemetry_data_old = {}

    while True:
        try:
            dht_sensor.measure()
            light = ldr.read()
        except:
            pass

        time.sleep(0.5)

        telemetry_data_new = pack_sensor_data(
            dht_sensor.temperature(), dht_sensor.humidity(), light)

        if telemetry_data_new != telemetry_data_old:
            send_data(telemetry_data_new)
            mqtt_client_publish(mqtt_client, MQTT_TOPIC, telemetry_data_new)
            telemetry_data_old = telemetry_data_new
        print()
        time.sleep(3)


if __name__ == "__main__":
    main()
