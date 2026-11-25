
import os
import time
import json
import threading
import paho.mqtt.client as mqtt

from dataset_reader import load_ppg_signal, create_batches

# ==========================================
# MQTT CONFIGURATION
# ==========================================

BROKER = "10.104.202.99"
PORT = 1883

TOPIC = "physicalai/ppg"
ACK_TOPIC = "physicalai/ppg/ack"
STATUS_TOPIC = "physicalai/ppg/status"
WAITING_TOPIC = "physicalai/ppg/waiting"

TRANSFER_ID = "bidmc01-2026-11-24-v2"

BATCH_INTERVAL = 2
ACK_TIMEOUT = 15
MAX_RETRIES = 3

TOTAL_BATCHES = 240
EXPECTED_SUBSCRIPTIONS = 2

USERNAME = "ppguser"
PASSWORD = os.getenv("PPG_MQTT_PASSWORD")

if not PASSWORD:
    raise RuntimeError(
        "Set PPG_MQTT_PASSWORD before starting publisher"
    )


# ==========================================
# THREADING EVENTS
# ==========================================

ack_condition = threading.Condition()

subscription_ready = threading.Event()

last_acknowledged = -1


# ==========================================
# STATUS MESSAGE
# ==========================================

def create_status_message(status):

    return json.dumps({
        "transfer_id": TRANSFER_ID,
        "role": "publisher",
        "status": status,
        "timestamp": time.time()
    })


# ==========================================
# MQTT CONNECTION CALLBACK
# ==========================================

def on_connect(client, userdata, flags, reason_code, properties):

    if reason_code == 0:

        print("\nConnected to Laptop 2 MQTT Broker")

        # Subscribe to both topics together.
        result, mid = client.subscribe([
            (ACK_TOPIC, 1),
            (WAITING_TOPIC, 1)
        ])

        if result != mqtt.MQTT_ERR_SUCCESS:
            print("Subscription request failed:", result)
            return

        print("Subscription requests sent:")
        print("1.", ACK_TOPIC)
        print("2.", WAITING_TOPIC)

        # Inform receiver that publisher is online.
        client.publish(
            STATUS_TOPIC,
            create_status_message("online"),
            qos=1,
            retain=True
        )

        print("Publisher status: ONLINE")

    else:

        print("Connection failed:", reason_code)


# ==========================================
# SUBSCRIPTION CALLBACK
# ==========================================

def on_subscribe(client, userdata, mid, reason_code_list, properties):

    print("\n========== MQTT SUBSCRIPTION STATUS ==========")

    for index, reason_code in enumerate(reason_code_list, start=1):

        print(
            f"Subscription {index}: {reason_code}"
        )

    successful = (
        len(reason_code_list) >= EXPECTED_SUBSCRIPTIONS
        and all(
            not getattr(code, "is_failure", False)
            for code in reason_code_list
        )
    )

    if successful:

        print("Both MQTT subscriptions confirmed.")
        subscription_ready.set()

    else:

        print("MQTT subscription failed or incomplete.")


# ==========================================
# RECEIVE MESSAGES FROM LAPTOP 2
# ==========================================

def on_message(client, userdata, msg):

    global last_acknowledged

    try:

        data = json.loads(
            msg.payload.decode("utf-8")
        )

        print("\nMQTT message received on:", msg.topic)

        if data.get("transfer_id") != TRANSFER_ID:
            print("Ignoring message from another transfer.")
            return

        # ----------------------------------
        # RECEIVER ACKNOWLEDGEMENT
        # ----------------------------------

        if msg.topic == ACK_TOPIC:

            batch_id = int(data["batch_id"])

            with ack_condition:

                last_acknowledged = max(
                    last_acknowledged,
                    batch_id
                )

                ack_condition.notify_all()

            print("Receiver ACK received:", batch_id)

            return

        # ----------------------------------
        # RECEIVER WAITING MESSAGE
        # ----------------------------------

        if msg.topic == WAITING_TOPIC:

            checkpoint = int(
                data.get("last_received_batch", 0)
            )

            next_batch = int(
                data.get(
                    "next_expected_batch",
                    checkpoint + 1
                )
            )

            with ack_condition:

                last_acknowledged = max(
                    last_acknowledged,
                    checkpoint
                )

                ack_condition.notify_all()

            print("\n")
            print("==============================================")
            print("       MESSAGE RECEIVED FROM LAPTOP 2")
            print("==============================================")

            print("Receiver role:", data.get("role"))
            print("Receiver status:", data.get("status"))

            print("\nMessage:")
            print(data.get("message"))

            print("\nLast saved batch:", checkpoint)
            print("Next expected batch:", next_batch)

            if data.get("status") == "waiting":

                print("\nReceiver is WAITING for remaining PPG data.")

            elif data.get("status") == "completed":

                print("\nReceiver has completed the PPG transfer.")

            print("==============================================")

            return

    except (ValueError, TypeError, KeyError) as error:

        print("Invalid MQTT message:", error)


# ==========================================
# MQTT CLIENT INITIALIZATION
# ==========================================

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="ppg_publisher"
)

client.username_pw_set(
    USERNAME,
    PASSWORD
)


# ==========================================
# LAST WILL FOR UNEXPECTED DISCONNECTION
# ==========================================

client.will_set(
    STATUS_TOPIC,
    create_status_message("offline"),
    qos=1,
    retain=True
)


# Register callbacks.

client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_message = on_message


# ==========================================
# WAIT FOR RECEIVER ACKNOWLEDGEMENT
# ==========================================

def wait_for_ack(batch_id):

    with ack_condition:

        return ack_condition.wait_for(
            lambda: last_acknowledged >= batch_id,
            timeout=ACK_TIMEOUT
        )


# ==========================================
# PPG TRANSMISSION
# ==========================================

def send_batches():

    global last_acknowledged

    signal = load_ppg_signal()

    batches = create_batches(signal)

    print("\n========== PPG MQTT TRANSMISSION ==========")
    print("Broker:", BROKER)
    print("Data topic:", TOPIC)
    print("Acknowledgement topic:", ACK_TOPIC)
    print("Waiting topic:", WAITING_TOPIC)
    print("Transfer ID:", TRANSFER_ID)
    print("Total batches:", len(batches))
    print("===========================================")

    client.connect(
        BROKER,
        PORT,
        60
    )

    client.loop_start()

    try:

        # ----------------------------------
        # WAIT FOR MQTT CONNECTION
        # ----------------------------------

        deadline = time.time() + 10

        while (
            not client.is_connected()
            and time.time() < deadline
        ):

            time.sleep(0.1)

        if not client.is_connected():

            raise ConnectionError(
                "Could not connect to MQTT broker"
            )

        # ----------------------------------
        # WAIT FOR BOTH SUBSCRIPTIONS
        # ----------------------------------

        print("\nWaiting for MQTT subscriptions...")

        if not subscription_ready.wait(timeout=15):

            raise TimeoutError(
                "Both MQTT subscriptions were not confirmed."
            )

        print("\nBoth subscriptions are ready.")

        # Give the broker time to deliver retained messages.
        time.sleep(2)

        # ----------------------------------
        # GET RECEIVER CHECKPOINT
        # ----------------------------------

        with ack_condition:

            checkpoint = max(
                0,
                last_acknowledged
            )

        print("\n========== RESUME INFORMATION ==========")

        print(
            "Receiver's last acknowledged batch:",
            checkpoint
        )

        if checkpoint < TOTAL_BATCHES:

            print(
                "Next batch to transmit:",
                checkpoint + 1
            )

        print("========================================")

        if checkpoint >= len(batches):

            print("All batches have already been acknowledged.")
            return

        successful = 0
        failed = 0

        # ----------------------------------
        # SEND REMAINING PPG BATCHES
        # ----------------------------------

        for batch in batches:

            batch_id = batch["batch_id"]

            # Skip already acknowledged batches.
            if batch_id <= checkpoint:
                continue

            data = {
                "sensor_id": "PPG_SENSOR_01",
                "transfer_id": TRANSFER_ID,
                **batch,
                "timestamp": time.time()
            }

            message = json.dumps(data)

            acknowledged = False

            # ----------------------------------
            # RETRY MECHANISM
            # ----------------------------------

            for attempt in range(1, MAX_RETRIES + 1):

                print(
                    f"\nSending Batch {batch_id} "
                    f"(Attempt {attempt}/{MAX_RETRIES})"
                )

                info = client.publish(
                    TOPIC,
                    message,
                    qos=1,
                    retain=False
                )

                info.wait_for_publish(timeout=10)

                if not info.is_published():

                    print("MQTT publish timed out.")
                    continue

                # Wait for receiver acknowledgement.
                if wait_for_ack(batch_id):

                    acknowledged = True

                    successful += 1

                    print("\n========== BATCH CONFIRMED ==========")

                    print("Batch ID:", batch_id)

                    print(
                        "Start Time:",
                        batch["start_time"],
                        "sec"
                    )

                    print(
                        "Sampling Frequency:",
                        batch["sampling_frequency"],
                        "Hz"
                    )

                    print(
                        "Samples Sent:",
                        batch["sample_count"]
                    )

                    print(
                        "First 10 Samples:",
                        batch["samples"][:10]
                    )

                    print(
                        "Receiver ACK:",
                        last_acknowledged
                    )

                    print(
                        "Status: Received and saved by Laptop 2"
                    )

                    print("=====================================")

                    break

                print(
                    "Acknowledgement not received. Retrying..."
                )

            if not acknowledged:

                failed += 1

                print(
                    f"\nStopping at Batch {batch_id}."
                )

                print(
                    "Restart later to resume from receiver checkpoint."
                )

                break

            if batch_id < len(batches):

                time.sleep(BATCH_INTERVAL)

        # ----------------------------------
        # TRANSMISSION SUMMARY
        # ----------------------------------

        print("\n========== TRANSMISSION SUMMARY ==========")

        print(
            "Batches acknowledged in this run:",
            successful
        )

        print("Failed batches:", failed)

        print(
            "Receiver checkpoint:",
            last_acknowledged
        )

        print(
            "Total dataset batches:",
            len(batches)
        )

        print("==========================================")

        if last_acknowledged == len(batches):

            print(
                "\nSUCCESS: ALL 240 BATCHES RECEIVED AND ACKNOWLEDGED!"
            )

    finally:

        # ----------------------------------
        # NORMAL OFFLINE NOTIFICATION
        # ----------------------------------

        if client.is_connected():

            print("\nSending publisher OFFLINE status...")

            info = client.publish(
                STATUS_TOPIC,
                create_status_message("offline"),
                qos=1,
                retain=True
            )

            info.wait_for_publish(timeout=5)

        client.disconnect()

        client.loop_stop()

        print("Publisher disconnected.")


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    try:

        send_batches()

    except KeyboardInterrupt:

        print("\nPublisher interrupted by user.")

    except Exception as error:

        print("\nPublisher error:", error)
