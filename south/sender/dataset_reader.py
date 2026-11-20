
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "south" / "dataset" / "bidmc_01_Signals.csv"

SAMPLING_FREQUENCY = 125
BATCH_DURATION = 2
SAMPLES_PER_BATCH = SAMPLING_FREQUENCY * BATCH_DURATION


def load_ppg_signal():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)

    # Remove extra spaces from column names
    df.columns = df.columns.str.strip()

    if "PLETH" not in df.columns:
        raise ValueError("PLETH column not found in dataset")

    signal = pd.to_numeric(df["PLETH"], errors="coerce")

    if signal.isna().any():
        raise ValueError("PPG signal contains missing or invalid values")

    return signal.to_numpy(dtype=float)


def create_batches(signal):
    batches = []

    for start in range(0, len(signal), SAMPLES_PER_BATCH):
        samples = signal[start:start + SAMPLES_PER_BATCH]

        if len(samples) < SAMPLES_PER_BATCH:
            break

        batch_number = len(batches) + 1
        start_time = start / SAMPLING_FREQUENCY

        batch = {
            "batch_id": batch_number,
            "start_time": round(start_time, 3),
            "sampling_frequency": SAMPLING_FREQUENCY,
            "duration_seconds": BATCH_DURATION,
            "sample_count": len(samples),
            "samples": samples.tolist()
        }

        batches.append(batch)

    return batches


if __name__ == "__main__":
    ppg_signal = load_ppg_signal()
    batches = create_batches(ppg_signal)

    print("PPG DATASET READER")
    print("---------------------------")
    print(f"Total samples: {len(ppg_signal)}")
    print(f"Sampling frequency: {SAMPLING_FREQUENCY} Hz")
    print(f"Batch duration: {BATCH_DURATION} seconds")
    print(f"Samples per batch: {SAMPLES_PER_BATCH}")
    print(f"Total complete batches: {len(batches)}")

    if batches:
        print("\nFirst batch details:")
        print(f"Batch ID: {batches[0]['batch_id']}")
        print(f"Start time: {batches[0]['start_time']} seconds")
        print(f"Sample count: {batches[0]['sample_count']}")
        print(f"First 10 PPG samples: {batches[0]['samples'][:10]}")
