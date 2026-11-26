
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent

INPUT_FILE = BASE / "received_ppg_filtered.csv"
OUTPUT_FILE = BASE / "received_signal_quality.csv"

FS = 125
WINDOW_SECONDS = 64
WINDOW_SAMPLES = FS * WINDOW_SECONDS


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    required = ["time_seconds", "ppg_raw", "ppg_filtered"]

    if not all(column in df.columns for column in required):
        raise ValueError("Filtered CSV is missing required columns.")

    if df.empty:
        raise ValueError("No PPG samples found.")

    if df[required].isnull().any().any():
        raise ValueError("Input CSV contains missing values.")

    time = df["time_seconds"].to_numpy(dtype=float)

    if len(time) > 1:
        estimated_fs = 1 / np.median(np.diff(time))

        if not np.isclose(estimated_fs, FS, atol=0.5):
            raise ValueError(
                f"Unexpected sampling frequency: {estimated_fs:.2f} Hz"
            )

    results = []

    for start in range(0, len(df), WINDOW_SAMPLES):
        section = df.iloc[start:start + WINDOW_SAMPLES]

        raw = section["ppg_raw"].to_numpy(dtype=float)
        filtered = section["ppg_filtered"].to_numpy(dtype=float)

        results.append({
            "start_time": float(section["time_seconds"].iloc[0]),
            "end_time": float(section["time_seconds"].iloc[-1]),
            "duration_seconds": len(section) / FS,
            "sample_count": len(section),
            "raw_range": float(np.ptp(raw)),
            "raw_std": float(np.std(raw)),
            "filtered_range": float(np.ptp(filtered)),
            "filtered_std": float(np.std(filtered))
        })

    quality_df = pd.DataFrame(results)
    quality_df.to_csv(OUTPUT_FILE, index=False)

    print("\nPPG SIGNAL QUALITY INDICATORS")
    print("-----------------------------")
    print(quality_df.round(5).to_string(index=False))

    print("\nTotal quality windows:", len(quality_df))
    print("Total samples:", len(df))
    print("Recording duration:", f"{len(df) / FS:.2f} seconds")
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
