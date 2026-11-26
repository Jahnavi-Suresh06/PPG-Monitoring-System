
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("signal_processing")

df = pd.read_csv(BASE / "received_ppg_filtered.csv")
detected = pd.read_csv(BASE / "received_pulse_detection.csv")

time = df["time_seconds"].to_numpy()
signal = df["ppg_filtered"].to_numpy()

# Additional candidates identified during inspection
candidate_times = [95.216, 95.856, 102.080, 102.648]

# Previously accepted peaks
accepted_times = detected.loc[
    detected["is_systolic_peak"],
    "time_seconds"
].to_numpy()

FS = 125
BEFORE = 0.30
AFTER = 0.50
POINTS = 100

def extract_pulse(peak_time):
    relative_time = np.linspace(-BEFORE, AFTER, POINTS)
    absolute_time = peak_time + relative_time

    pulse = np.interp(absolute_time, time, signal)

    # Normalize for shape comparison only
    pulse = pulse - np.min(pulse)

    amplitude_range = np.max(pulse)

    if amplitude_range > 0:
        pulse = pulse / amplitude_range

    return relative_time, pulse

fig, axes = plt.subplots(2, 2, figsize=(13, 9))

for ax, candidate in zip(axes.flat, candidate_times):

    relative_time, candidate_pulse = extract_pulse(candidate)

    ax.plot(
        relative_time,
        candidate_pulse,
        color="orange",
        linewidth=2,
        label=f"Candidate {candidate:.3f}s"
    )

    # Compare with nearby accepted peaks
    nearby = accepted_times[
        np.abs(accepted_times - candidate) <= 2.0
    ]

    for reference in nearby:
        _, reference_pulse = extract_pulse(reference)

        ax.plot(
            relative_time,
            reference_pulse,
            alpha=0.65,
            linewidth=1.3,
            label=f"Accepted {reference:.3f}s"
        )

    ax.axvline(0, linestyle="--", color="gray")
    ax.set_title(f"Candidate at {candidate:.3f} seconds")
    ax.set_xlabel("Time relative to peak (seconds)")
    ax.set_ylabel("Normalized amplitude")
    ax.grid(True)
    ax.legend(fontsize=8)

plt.tight_layout()

output = BASE / "received_pulse_shape_comparison.png"
plt.savefig(output, dpi=150)

print("Saved:", output)
plt.show()
