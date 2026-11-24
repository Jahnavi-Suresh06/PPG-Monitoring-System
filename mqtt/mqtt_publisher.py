
import paho.mqtt.client as mqtt
import json
import time
import random

BROKER = "localhost"
PORT = 1883
TOPIC = "physicalai/ppg"

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="ppg_publisher"
)

print("Connecting to MQTT Broker...")
client.connect(BROKER, PORT, 60)
client.loop_start()

try:
    batch_id = 1

    while True:

        data = {
            "sensor_id": "PPG_SENSOR_01",
            "batch_id": batch_id,
            "sampling_frequency": 125,
            "samples": [
                round(0.4 + random.uniform(-0.02, 0.02), 5)
                for _ in range(10)
            ],
            "timestamp": time.time()
        }

        message = json.dumps(data)

        info = client.publish(
            TOPIC,
            message,
            qos=1,
            retain=False
        )

        info.wait_for_publish()

        print("\nMESSAGE SENT")
        print("Topic:", TOPIC)
        print("Message:", message)

        batch_id += 1
        time.sleep(2)

except KeyboardInterrupt:
    print("\nPublisher stopped.")

finally:
    client.loop_stop()
    client.disconnect()
