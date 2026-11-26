import pandas as pd
from pathlib import Path

# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    PROJECT_ROOT
    / "south"
    / "dataset"
    / "bidmc_01_Signals.csv"
)

SAMPLING_FREQUENCY = 125
BATCH_DURATION = 0.8
SAMPLES_PER_BATCH = int(SAMPLING_FREQUENCY * BATCH_DURATION)

# 50 batches x 100 samples = 5,000 samples = 40 seconds
MAX_BATCHES = 50


# --------------------------------------------------
# LOAD PPG SIGNAL
# --------------------------------------------------

def load_ppg_signal():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    df.columns = df.columns.str.strip()

    if "PLETH" not in df.columns:
        raise ValueError("PLETH column not found in dataset")

    signal = pd.to_numeric(df["PLETH"], errors="coerce")

    if signal.isna().any():
        raise ValueError("PPG signal contains missing or invalid values")

    return signal.to_numpy(dtype=float)


# --------------------------------------------------
# CREATE PPG BATCHES
# --------------------------------------------------

def create_batches(signal):
    required_samples = MAX_BATCHES * SAMPLES_PER_BATCH

    if len(signal) < required_samples:
        raise ValueError(
            f"Dataset has only {len(signal)} samples; "
            f"{required_samples} are required for {MAX_BATCHES} complete batches."
        )

    batches = []

    for batch_index in range(MAX_BATCHES):
        start = batch_index * SAMPLES_PER_BATCH
        end = start + SAMPLES_PER_BATCH
        samples = signal[start:end]

        batches.append({
            "batch_id": batch_index + 1,
            "start_time": round(start / SAMPLING_FREQUENCY, 3),
            "sampling_frequency": SAMPLING_FREQUENCY,
            "duration_seconds": BATCH_DURATION,
            "sample_count": len(samples),
            "samples": samples.tolist(),
        })

    return batches


# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------

if __name__ == "__main__":
    ppg_signal = load_ppg_signal()
    batches = create_batches(ppg_signal)

    total_samples = sum(batch["sample_count"] for batch in batches)
    total_duration = total_samples / SAMPLING_FREQUENCY

    print("\nPPG DATASET READER")
    print("---------------------------")
    print(f"Dataset samples available: {len(ppg_signal)}")
    print(f"Sampling frequency: {SAMPLING_FREQUENCY} Hz")
    print(f"Batch duration: {BATCH_DURATION} seconds")
    print(f"Samples per batch: {SAMPLES_PER_BATCH}")
    print(f"Maximum batches: {MAX_BATCHES}")
    print(f"Total complete batches: {len(batches)}")
    print(f"Total transmitted samples: {total_samples}")
    print(f"Total transmitted duration: {total_duration:.2f} seconds")

    print("\nALL BATCH DETAILS")
    print("---------------------------")
    for batch in batches:
        print(
            f"Batch {batch['batch_id']:02d}: "
            f"{batch['sample_count']} samples, "
            f"start={batch['start_time']:.1f} seconds"
        )

    print("\nFirst 10 samples of batch 1:")
    print(batches[0]["samples"][:10])
