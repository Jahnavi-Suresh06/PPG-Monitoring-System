
import os
import time
import requests

from dataset_reader import load_ppg_signal, create_batches


API_URL = os.getenv(
    "PPG_API_URL",
    "http://127.0.0.1:8000/api/ppg/batch"
)

COMPLETE_URL = os.getenv(
    "PPG_COMPLETE_URL",
    API_URL.rsplit("/", 1)[0] + "/complete"
)

BATCH_INTERVAL = 0.8


def send_batches():
    signal = load_ppg_signal()
    batches = create_batches(signal)

    print("PPG DATA TRANSMISSION")
    print("-----------------------------")
    print(f"Total batches: {len(batches)}")
    print(f"API endpoint: {API_URL}")
    print()

    successful_batches = 0
    failed_batches = 0

    for batch in batches:
        try:
            response = requests.post(
                API_URL,
                json=batch,
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            successful_batches += 1

            print("\n========== PPG BATCH CONFIRMATION ==========")
            print(f"Record ID: {result['record_id']}")
            print(f"Batch ID: {result['batch_id']}")
            print(f"Start Time: {result['start_time']} sec")
            print(f"Sampling Frequency: {result['sampling_frequency']} Hz")
            print(f"Samples Received: {result['samples_received']}")
            print(f"First 10 Samples: {result['samples']}")
            print("Status: Successfully received and stored")
            print("============================================")

        except requests.RequestException as error:
            failed_batches += 1
            print(f"Batch {batch['batch_id']} failed: {error}")

        if batch["batch_id"] < len(batches):
            time.sleep(BATCH_INTERVAL)

    print("\nTRANSMISSION SUMMARY")
    print("-----------------------------")
    print(f"Successful batches: {successful_batches}")
    print(f"Failed batches: {failed_batches}")
    print(f"Total batches: {len(batches)}")

    if failed_batches == 0:
        try:
            response = requests.post(
                COMPLETE_URL,
                timeout=10
            )
            response.raise_for_status()

            print("\nPPG TRANSMISSION COMPLETED SUCCESSFULLY")

        except requests.RequestException as error:
            print(f"Could not update transmission status: {error}")


if __name__ == "__main__":
    send_batches()
