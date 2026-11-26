import json
import os
from pathlib import Path

import mysql.connector
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.signal import butter, sosfiltfilt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "signal_processing" / "received_ppg_filtered.csv"

SAMPLING_FREQUENCY = 125
EXPECTED_BATCHES = 32
SAMPLES_PER_BATCH = 250
BATCH_DURATION = 2.0


def load_signal_from_mysql():
    load_dotenv(PROJECT_ROOT / ".env")

    required = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing MySQL settings in .env: " + ", ".join(missing))

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3307")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT batch_id, start_time, sampling_frequency,
                   duration_seconds, sample_count, samples_json
            FROM ppg_batches
            ORDER BY batch_id ASC
        """)
        rows = cursor.fetchall()
        cursor.close()
    finally:
        connection.close()

    if len(rows) != EXPECTED_BATCHES:
        raise ValueError(
            f"Expected {EXPECTED_BATCHES} batches in MySQL, found {len(rows)}."
        )

    expected_ids = list(range(1, EXPECTED_BATCHES + 1))
    actual_ids = [int(row["batch_id"]) for row in rows]
    if actual_ids != expected_ids:
        raise ValueError(f"Expected batch IDs 1–32, found {actual_ids}")

    signal_batches = []
    for row in rows:
        batch_id = int(row["batch_id"])
        if int(row["sampling_frequency"]) != SAMPLING_FREQUENCY:
            raise ValueError(
                f"Batch {batch_id} has an unexpected sampling frequency.")
        if int(row["sample_count"]) != SAMPLES_PER_BATCH:
            raise ValueError(f"Batch {batch_id} does not contain 250 samples.")
        if not np.isclose(float(row["duration_seconds"]), BATCH_DURATION, atol=1e-6):
            raise ValueError(f"Batch {batch_id} has an unexpected duration.")
        expected_start = (batch_id - 1) * BATCH_DURATION
        if not np.isclose(float(row["start_time"]), expected_start, atol=0.001):
            raise ValueError(
                f"Batch {batch_id} starts at {row['start_time']}, "
                f"expected {expected_start}."
            )

        samples_value = row["samples_json"]
        if isinstance(samples_value, (bytes, bytearray)):
            samples_value = samples_value.decode("utf-8")
        samples = samples_value if isinstance(
            samples_value, list) else json.loads(samples_value)

        if len(samples) != SAMPLES_PER_BATCH:
            raise ValueError(
                f"Batch {batch_id} JSON does not contain 250 samples.")

        signal_batches.append(np.asarray(samples, dtype=float))

    signal = np.concatenate(signal_batches)
    if len(signal) != EXPECTED_BATCHES * SAMPLES_PER_BATCH:
        raise ValueError(f"Expected 8000 samples, found {len(signal)}.")
    if not np.all(np.isfinite(signal)):
        raise ValueError("The MySQL PPG recording contains non-finite values.")

    return signal


def filter_ppg_signal(ppg_raw):
    sos = butter(
        4,
        [0.5, 8.0],
        btype="bandpass",
        fs=SAMPLING_FREQUENCY,
        output="sos",
    )
    return sosfiltfilt(sos, ppg_raw)


def main():
    print("PPG SIGNAL PROCESSING FROM MYSQL")
    print("--------------------------------")
    ppg_raw = load_signal_from_mysql()

    total_samples = len(ppg_raw)
    duration = total_samples / SAMPLING_FREQUENCY
    ppg_filtered = filter_ppg_signal(ppg_raw)
    time_seconds = np.arange(total_samples) / SAMPLING_FREQUENCY

    output = pd.DataFrame({
        "time_seconds": time_seconds,
        "ppg_raw": ppg_raw,
        "ppg_filtered": ppg_filtered,
    })
    output.to_csv(OUTPUT_PATH, index=False)

    print(f"Sampling frequency: {SAMPLING_FREQUENCY} Hz")
    print(f"Total batches: {EXPECTED_BATCHES}")
    print(f"Samples per batch: {SAMPLES_PER_BATCH}")
    print(f"Total samples: {total_samples}")
    print(f"Signal duration: {duration:.2f} seconds")
    print(f"Filtered signal mean: {np.mean(ppg_filtered):.6f}")
    print(f"Filtered signal standard deviation: {np.std(ppg_filtered):.6f}")
    print(f"Saved filtered waveform: {OUTPUT_PATH}")
    print("Filtering completed successfully.")


if __name__ == "__main__":
    main()
