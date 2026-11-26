
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
INPUT_FILE = BASE / "received_pulse_detection.csv"

SUMMARY_FILE = BASE / "analysis_batch_summary.csv"
WAVEFORM_FILE = BASE / "analysis_batch_waveforms.csv"

PULSES_PER_BATCH = 32
NUMBER_OF_BATCHES = 5
TARGET_PULSES = PULSES_PER_BATCH * NUMBER_OF_BATCHES


def main():
    df = pd.read_csv(INPUT_FILE)

    required = {
        "time_seconds",
        "ppg_filtered",
        "is_systolic_peak",
        "is_valley",
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    time = df["time_seconds"].to_numpy(dtype=float)
    signal = df["ppg_filtered"].to_numpy(dtype=float)

    peaks = np.flatnonzero(
        df["is_systolic_peak"].astype(bool).to_numpy()
    )
    valleys = np.flatnonzero(
        df["is_valley"].astype(bool).to_numpy()
    )

    if len(peaks) == 0 or len(valleys) < 2:
        raise ValueError("Not enough detected peaks or valleys.")

    pulse_records = []
    waveform_records = []

    for peak in peaks:
        # Find the nearest valley before and after this peak.
        before = valleys[valleys < peak]
        after = valleys[valleys > peak]

        if len(before) == 0 or len(after) == 0:
            continue

        start = int(before[-1])
        end = int(after[0])

        if not (start < peak < end):
            continue

        segment = signal[start:end + 1]
        segment_time = time[start:end + 1]

        if len(segment) < 3:
            continue

        if not np.all(np.isfinite(segment)):
            continue

        pulse_records.append({
            "peak_index": int(peak),
            "start_index": start,
            "end_index": end,
            "start_time": float(time[start]),
            "peak_time": float(time[peak]),
            "end_time": float(time[end]),
            "duration_seconds": float(time[end] - time[start]),
        })

    if len(pulse_records) < TARGET_PULSES:
        raise ValueError(
            f"Only {len(pulse_records)} complete pulses found. "
            f"Need {TARGET_PULSES}."
        )

    # Use the first 160 valid pulses for this initial implementation.
    pulse_records = pulse_records[:TARGET_PULSES]

    for i, pulse in enumerate(pulse_records):
        batch_id = (i // PULSES_PER_BATCH) + 1
        pulse_number = (i % PULSES_PER_BATCH) + 1

        pulse.update({
            "analysis_batch_id": batch_id,
            "pulse_number": pulse_number,
            "global_pulse_number": i + 1,
        })

        start = pulse["start_index"]
        end = pulse["end_index"]
        peak = pulse["peak_index"]

        for sample_index in range(start, end + 1):
            waveform_records.append({
                "analysis_batch_id": batch_id,
                "pulse_number": pulse_number,
                "global_pulse_number": i + 1,
                "sample_index": sample_index,
                "time_seconds": float(time[sample_index]),
                "relative_time_seconds": float(
                    time[sample_index] - time[start]
                ),
                "ppg_filtered": float(signal[sample_index]),
                "is_systolic_peak": sample_index == peak,
                "is_start_valley": sample_index == start,
                "is_end_valley": sample_index == end,
            })

    summary = pd.DataFrame(pulse_records)
    waveforms = pd.DataFrame(waveform_records)

    summary.to_csv(SUMMARY_FILE, index=False)
    waveforms.to_csv(WAVEFORM_FILE, index=False)

    print("\nANALYSIS BATCH CREATION")
    print("----------------------")
    print("Complete pulses:", len(summary))
    print("Analysis batches:", summary["analysis_batch_id"].nunique())
    print("Pulses per batch:", PULSES_PER_BATCH)

    print("\nBatch counts:")
    print(summary.groupby("analysis_batch_id").size())

    print("\nSaved:")
    print(SUMMARY_FILE)
    print(WAVEFORM_FILE)


if __name__ == "__main__":
    main()
