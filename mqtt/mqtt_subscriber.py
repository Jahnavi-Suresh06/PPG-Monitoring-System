
import paho.mqtt.client as mqtt
import json

BROKER = "localhost"
PORT = 1883
TOPIC = "physicalai/ppg"


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT Broker")
        client.subscribe(TOPIC, qos=1)
        print("Subscribed to:", TOPIC)
    else:
        print("Connection failed:", reason_code)


def on_message(client, userdata, msg):

    message = msg.payload.decode("utf-8")

    print("\nMESSAGE RECEIVED")
    print("---------------------------")
    print("Topic:", msg.topic)
    print("Message:", message)
    print("---------------------------")


client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="ppg_subscriber"
)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT Broker...")
client.connect(BROKER, PORT, 60)

client.loop_forever()
