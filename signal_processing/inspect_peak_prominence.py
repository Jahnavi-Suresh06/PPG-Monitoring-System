
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from pathlib import Path

BASE = Path("signal_processing")

df = pd.read_csv(BASE / "received_ppg_filtered.csv")

time = df["time_seconds"].to_numpy()
signal = df["ppg_filtered"].to_numpy()

FS = 125
MIN_DISTANCE = int(0.30 * FS)
PROMINENCE = 0.05 * np.std(signal)
peaks, properties = find_peaks(
    signal,
    distance=MIN_DISTANCE,
    prominence=0
)

peak_df = pd.DataFrame({
    "peak_time": time[peaks],
    "amplitude": signal[peaks],
    "prominence": properties["prominences"]
})

windows = [
    (43.7, 45.4),
    (94.0, 97.3),
    (100.7, 103.8)
]

print("\nPEAK PROMINENCE INSPECTION")
print("--------------------------")
print("Current prominence threshold:", round(PROMINENCE, 6))

for start, end in windows:

    section = peak_df[
        (peak_df["peak_time"] >= start) &
        (peak_df["peak_time"] <= end)
    ]

    print(f"\nRegion: {start}–{end} seconds")
    print(section.round(5).to_string(index=False))

print("\nInspection completed.")
