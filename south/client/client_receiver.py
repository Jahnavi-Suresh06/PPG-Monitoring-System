
import requests
import time

SERVER_URL = "http://10.104.202.164:8000"
def receive_ppg_data():

    print("PPG RECEIVER CLIENT")
    print("==============================")
    print(f"Server: {SERVER_URL}")
    print("Waiting for PPG data...\n")

    last_record_id = 0

    while True:
        try:
            # Fetch new PPG batches
            response = requests.get(
                f"{SERVER_URL}/api/ppg/batches",
                params={
                    "after_id": last_record_id,
                    "limit": 20
                },
                timeout=5
            )

            response.raise_for_status()
            batches = response.json()["batches"]

            if batches:
                for batch in batches:
                    print("PPG DATA RECEIVED")
                    print("------------------------------")
                    print(f"Record ID: {batch['record_id']}")
                    print(f"Batch ID: {batch['batch_id']}")
                    print(f"Start Time: {batch['start_time']} sec")
                    print(f"Sampling Frequency: {batch['sampling_frequency']} Hz")
                    print(f"Samples Received: {batch['sample_count']}")
                    print(f"First 10 Samples: {batch['samples'][:10]}")
                    print()

                    last_record_id = batch["record_id"]

            # Check transmission status
            status_response = requests.get(
                f"{SERVER_URL}/api/ppg/status",
                timeout=5
            )

            status_response.raise_for_status()
            status = status_response.json()

            # Stop only after completion and receiving all pending batches
            if status["transmission_completed"] and not batches:
                print("================================")
                print("PPG TRANSMISSION COMPLETED")
                print("All available batches received.")
                print("Receiver stopped.")
                break

            time.sleep(2)

        except requests.RequestException as error:
            print(f"Connection error: {error}")
            time.sleep(3)


if __name__ == "__main__":
    receive_ppg_data()
