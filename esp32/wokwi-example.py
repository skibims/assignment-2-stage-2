from machine import Pin, ADC
from umqtt.simple import MQTTClient
import ujson
import network
import utime as time
import dht
import urequests as requests

ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)
DEVICE_ID = "esp32-sic6"
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""
TOKEN = "BBUS-tMi16kPrI16pVtswdckwitYhXZwAls"
DHT_PIN = Pin(15)

def did_receive_callback(topic, message):
    print('\n\nData Received! \ntopic = {0}, message = {1}'.format(topic, message))

# def mqtt_connect():
#     print("Connecting to MQTT broker ...", end="")
#     mqtt_client = MQTTClient(MQTT_CLIENT, MQTT_BROKER, user="", password="")
#     mqtt_client.set_callback(did_receive_callback)
#     mqtt_client.connect()
#     print("Connected.")
#     mqtt_client.subscribe(MQTT_CONTROL_TOPIC)
#     return mqtt_client

def create_json_data(temperature, humidity, light):
    data = ujson.dumps({
        "device_id": DEVICE_ID,
        "temp": temperature,
        "humidity": humidity,
        "light": light,
        "type": "sensor"
    })
    return data

# def mqtt_client_publish(topic, data):
#     print("\nUpdating MQTT Broker...")
#     mqtt_client.publish(topic, data)
#     print(data)

def send_data(temperature, humidity, light):
    url = "http://industrial.api.ubidots.com/api/v1.6/devices/" + DEVICE_ID
    headers = {"Content-Type": "application/json", "X-Auth-Token": TOKEN}
    data = {
        "temp": temperature,
        "humidity": humidity,
        "ldr_value": light
    }
    response = requests.post(url, json=data, headers=headers)
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

# mqtt_client = mqtt_connect()
# mqtt_client_publish(MQTT_CONTROL_TOPIC, 'LOVELY')
dht_sensor = dht.DHT22(DHT_PIN)
telemetry_data_old = ""

while True:
    # mqtt_client.check_msg()
    # print(". ", end="")
    try:
        dht_sensor.measure()
        ldr_value = ldr.read()
    except:
        pass

    time.sleep(0.5)

    telemetry_data_new = create_json_data(dht_sensor.temperature(), dht_sensor.humidity(), ldr_value)

    if telemetry_data_new != telemetry_data_old:
        # mqtt_client_publish(MQTT_TELEMETRY_TOPIC, telemetry_data_new)
        telemetry_data_old = telemetry_data_new
        
        # Call the send_data function to send data to Ubidots
        send_data(dht_sensor.temperature(), dht_sensor.humidity(), ldr_value)
    
    time.sleep(0.3)
