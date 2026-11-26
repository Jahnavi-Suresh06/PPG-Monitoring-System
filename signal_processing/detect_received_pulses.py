
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from pathlib import Path

BASE = Path(__file__).resolve().parent

INPUT_FILE = BASE / "received_ppg_filtered.csv"
OUTPUT_FILE = BASE / "received_pulse_detection.csv"
PLOT_FILE = BASE / "received_pulse_detection.png"

FS = 125

# Minimum time between two systolic peaks
MIN_PULSE_INTERVAL_SEC = 0.30

# Initial exploratory prominence setting
PROMINENCE_FACTOR = 0.10


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    required_columns = {"time_seconds", "ppg_filtered"}
    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"Missing required columns: {required_columns - set(df.columns)}"
        )

    time = df["time_seconds"].to_numpy(dtype=float)
    signal = df["ppg_filtered"].to_numpy(dtype=float)

    if len(time) != len(signal):
        raise ValueError("Time and signal lengths do not match.")

    if len(signal) < 2:
        raise ValueError("Not enough samples for pulse detection.")

    if not np.all(np.isfinite(time)) or not np.all(np.isfinite(signal)):
        raise ValueError("Time or signal contains invalid values.")

    if not np.all(np.diff(time) > 0):
        raise ValueError("Time values must be strictly increasing.")

    # Verify sampling frequency
    estimated_fs = 1 / np.median(np.diff(time))

    if not np.isclose(estimated_fs, FS, atol=0.5):
        raise ValueError(f"Unexpected sampling frequency: {estimated_fs}")

    total_samples = len(signal)
    duration = total_samples / FS

    print("\nRECEIVED PPG PULSE DETECTION")
    print("---------------------------")
    print(f"Sampling frequency: {FS} Hz")
    print(f"Total samples: {total_samples}")
    print(f"Signal duration: {duration:.2f} seconds")
    print(f"Time axis last value: {time[-1]:.3f} seconds")

    # Detect systolic peaks and valleys
    min_distance = int(MIN_PULSE_INTERVAL_SEC * FS)
    prominence = PROMINENCE_FACTOR * np.std(signal)

    peaks, peak_properties = find_peaks(
        signal,
        distance=min_distance,
        prominence=prominence
    )

    valleys, valley_properties = find_peaks(
        -signal,
        distance=min_distance,
        prominence=prominence
    )

    print(f"\nDetected systolic peaks: {len(peaks)}")
    print(f"Detected valleys: {len(valleys)}")

    # Save detected points
    result = pd.DataFrame({
        "time_seconds": time,
        "ppg_filtered": signal,
        "is_systolic_peak": False,
        "is_valley": False
    })

    result.loc[peaks, "is_systolic_peak"] = True
    result.loc[valleys, "is_valley"] = True

    result.to_csv(OUTPUT_FILE, index=False)

    # Estimate heart rate from consecutive systolic peaks
    if len(peaks) >= 2:
        peak_times = time[peaks]
        intervals = np.diff(peak_times)
        heart_rates = 60 / intervals

        print("\nINITIAL HEART RATE ESTIMATE")
        print("--------------------------")
        print(f"Median HR: {np.median(heart_rates):.2f} BPM")
        print(f"Mean HR: {np.mean(heart_rates):.2f} BPM")
        print(f"Minimum HR: {np.min(heart_rates):.2f} BPM")
        print(f"Maximum HR: {np.max(heart_rates):.2f} BPM")
    else:
        print("\nNot enough peaks to estimate heart rate.")

    # Plot first 20 seconds
    plot_end = min(20.0, duration)
    mask = time <= plot_end

    plt.figure(figsize=(15, 6))

    plt.plot(
        time[mask],
        signal[mask],
        label="Filtered PPG"
    )

    visible_peaks = peaks[time[peaks] <= plot_end]
    visible_valleys = valleys[time[valleys] <= plot_end]

    plt.scatter(
        time[visible_peaks],
        signal[visible_peaks],
        color="red",
        label="Systolic peaks"
    )

    plt.scatter(
        time[visible_valleys],
        signal[visible_valleys],
        color="green",
        label="Valleys"
    )

    plt.xlabel("Time (seconds)")
    plt.ylabel("PPG amplitude")
    plt.title("Received PPG - Pulse Detection (First 20 Seconds)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(PLOT_FILE, dpi=150)
    plt.show()

    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Saved: {PLOT_FILE}")
    print("\nPulse detection completed.")


if __name__ == "__main__":
    main()
