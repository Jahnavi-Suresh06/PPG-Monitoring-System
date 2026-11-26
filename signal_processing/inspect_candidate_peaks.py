
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from pathlib import Path

BASE = Path("signal_processing")

df = pd.read_csv(BASE / "received_ppg_filtered.csv")

time = df["time_seconds"].to_numpy()
signal = df["ppg_filtered"].to_numpy()

FS = 125
MIN_DISTANCE = int(0.30 * FS)

# Original detection threshold
original_threshold = 0.10 * np.std(signal)

# Original detected peaks
original_peaks, _ = find_peaks(
    signal,
    distance=MIN_DISTANCE,
    prominence=original_threshold
)

# All local peak candidates
all_peaks, properties = find_peaks(
    signal,
    distance=MIN_DISTANCE,
    prominence=0
)

# Candidates not detected by original threshold
additional_peaks = np.setdiff1d(all_peaks, original_peaks)

windows = [
    (94.0, 97.3, "Region 1: 94–97 seconds"),
    (100.7, 103.8, "Region 2: 100–104 seconds")
]

fig, axes = plt.subplots(2, 1, figsize=(16, 10))

for ax, (start, end, title) in zip(axes, windows):

    section = (time >= start) & (time <= end)

    original_in_window = original_peaks[
        (time[original_peaks] >= start) &
        (time[original_peaks] <= end)
    ]

    additional_in_window = additional_peaks[
        (time[additional_peaks] >= start) &
        (time[additional_peaks] <= end)
    ]

    ax.plot(
        time[section],
        signal[section],
        color="blue",
        linewidth=1,
        label="Filtered PPG"
    )

    ax.scatter(
        time[original_in_window],
        signal[original_in_window],
        color="red",
        s=65,
        label="Original detected peaks",
        zorder=3
    )

    ax.scatter(
        time[additional_in_window],
        signal[additional_in_window],
        color="orange",
        s=75,
        marker="x",
        label="Additional candidates",
        zorder=4
    )

    ax.set_title(title)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Amplitude")
    ax.grid(True)
    ax.legend()

plt.tight_layout()

output = BASE / "candidate_peak_comparison.png"
plt.savefig(output, dpi=150)
plt.show()

print("Original prominence threshold:", round(original_threshold, 6))
print("Original detected peaks:", len(original_peaks))
print("Additional candidates:", len(additional_peaks))
print("Saved:", output)
