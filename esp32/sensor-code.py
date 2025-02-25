from machine import Pin, ADC
from umqtt.simple import MQTTClient
import ujson
import network
import utime as time
import dht
import urequests as requests

ldr = ADC(Pin(32))
ldr.atten(ADC.ATTN_11DB)
MQTT_CLIENT_ID = "skibims"
MQTT_BROKER       = "broker.emqx.io"
MQTT_TOPIC = "/UNI169/skibims/sensor"
DEVICE_ID = "esp32-sic6"
WIFI_SSID = "POCO F4"
WIFI_PASSWORD = "CharZaku"
TOKEN = "BBUS-tMi16kPrI16pVtswdckwitYhXZwAls"
DHT_PIN = Pin(15)
mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, user="", password="")

def did_receive_callback(topic, message):
    print('\n\nData Received! \ntopic = {0}, message = {1}'.format(topic, message))

def mqtt_connect():
    print("Connecting to MQTT broker ...", end="")
    mqtt_client.set_callback(did_receive_callback)
    mqtt_client.connect()
    print("Connected.")
    return mqtt_client

def create_json_data(temperature, humidity, light):
    data = ujson.dumps({
        "device_id": DEVICE_ID,
        "temp": temperature,
        "humidity": humidity,
        "light": light,
        "type": "sensor"
    })
    return data

def mqtt_client_publish(topic, data):
    print("\nUpdating MQTT Broker...")
    mqtt_client.publish(topic, data)
    print(data)

def send_data(json):
    url = "http://industrial.api.ubidots.com/api/v1.6/devices/" + DEVICE_ID
    headers = {"Content-Type": "application/json", "X-Auth-Token": TOKEN}
    response = requests.post(url, json=json, headers=headers)
    print("Response:", response.text)

wifi_client = network.WLAN(network.STA_IF)
wifi_client.active(True)
print("Connecting device to WiFi")
wifi_client.connect(WIFI_SSID, WIFI_PASSWORD)

while not wifi_client.isconnected():
    print("Connecting")
    time.sleep(0.1)
print("WiFi Connected!")
print(wifi_client.ifconfig())

mqtt_client = mqtt_connect()
dht_sensor = dht.DHT11(DHT_PIN)
telemetry_data_old = ""
light = ""

while True:
    try:
        dht_sensor.measure()
        light = ldr.read()
    except:
        pass

    time.sleep(0.5)

    telemetry_data_new = create_json_data(dht_sensor.temperature(), dht_sensor.humidity(), light)

    if telemetry_data_new != telemetry_data_old:
        mqtt_client_publish(MQTT_TOPIC, telemetry_data_new)
        telemetry_data_old = telemetry_data_new
        
        # Call the send_data function to send data to Ubidots
        send_data(telemetry_data_new)
    
    time.sleep(0.3)
