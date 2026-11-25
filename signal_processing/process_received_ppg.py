
import sqlite3
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "ppg_monitoring.db"
OUTPUT_PATH = PROJECT_ROOT / "signal_processing" / "received_ppg_filtered.csv"

# PPG configuration
SAMPLING_FREQUENCY = 125
EXPECTED_BATCHES = 240
SAMPLES_PER_BATCH = 250

def load_latest_ppg_signal():
    connection = sqlite3.connect(DATABASE_PATH)

    rows = connection.execute("""
        SELECT id, batch_id, sample_count, samples_json
        FROM ppg_batches
        ORDER BY id DESC
        LIMIT ?
    """, (EXPECTED_BATCHES,)).fetchall()

    connection.close()

    # Restore chronological order
    rows.reverse()

    if len(rows) != EXPECTED_BATCHES:
        raise ValueError(
            f"Expected {EXPECTED_BATCHES} batches, found {len(rows)}"
        )

    batch_ids = [row[1] for row in rows]

    if batch_ids != list(range(1, EXPECTED_BATCHES + 1)):
        raise ValueError(
            "Latest records do not contain exactly batches 1 to 240."
        )

    signal_batches = []

    for record_id, batch_id, sample_count, samples_json in rows:
        samples = json.loads(samples_json)

        if sample_count != SAMPLES_PER_BATCH:
            raise ValueError(f"Invalid sample count in batch {batch_id}")

        if len(samples) != SAMPLES_PER_BATCH:
            raise ValueError(f"Invalid waveform length in batch {batch_id}")

        signal_batches.append(np.asarray(samples, dtype=float))

    signal = np.concatenate(signal_batches)

    if not np.all(np.isfinite(signal)):
        raise ValueError("PPG signal contains invalid values.")

    return signal


def filter_ppg_signal(ppg_raw):
    low_cutoff = 0.5
    high_cutoff = 8.0
    filter_order = 4

    sos = butter(
        filter_order,
        [low_cutoff, high_cutoff],
        btype="bandpass",
        fs=SAMPLING_FREQUENCY,
        output="sos"
    )

    ppg_filtered = sosfiltfilt(sos, ppg_raw)

    return ppg_filtered


def main():
    print("PPG SIGNAL PROCESSING")
    print("-----------------------------")

    ppg_raw = load_latest_ppg_signal()

    total_samples = len(ppg_raw)
    duration = total_samples / SAMPLING_FREQUENCY

    print(f"Sampling frequency: {SAMPLING_FREQUENCY} Hz")
    print(f"Total batches: {EXPECTED_BATCHES}")
    print(f"Total samples: {total_samples}")
    print(f"Signal duration: {duration:.2f} seconds")

    ppg_filtered = filter_ppg_signal(ppg_raw)

    time_seconds = (
        np.arange(total_samples) / SAMPLING_FREQUENCY
    )

    output = pd.DataFrame({
        "time_seconds": time_seconds,
        "ppg_raw": ppg_raw,
        "ppg_filtered": ppg_filtered
    })

    output.to_csv(OUTPUT_PATH, index=False)

    print("\nFILTERING COMPLETED SUCCESSFULLY")
    print(f"Output file: {OUTPUT_PATH}")
    print(f"Raw signal samples: {len(ppg_raw)}")
    print(f"Filtered signal samples: {len(ppg_filtered)}")
    print(f"Filtered signal mean: {np.mean(ppg_filtered):.5f}")
    print(f"Filtered signal standard deviation: {np.std(ppg_filtered):.5f}")


if __name__ == "__main__":
    main()
