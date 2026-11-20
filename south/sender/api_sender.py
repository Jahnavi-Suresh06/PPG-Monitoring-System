
import time
import requests

from dataset_reader import load_ppg_signal, create_batches

API_URL = "http://127.0.0.1:8000/api/ppg/batch"
BATCH_INTERVAL = 2


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

            print(
                f"Batch {batch['batch_id']} sent successfully | "
                f"Samples: {result['samples_received']} | "
                f"Start time: {batch['start_time']}s"
            )

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


if __name__ == "__main__":
    send_batches()
