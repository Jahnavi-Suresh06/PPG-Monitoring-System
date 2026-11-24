
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("signal_processing")

# Load the required files
filtered = pd.read_csv(BASE / "pleth1_filtered.csv")
morphology = pd.read_csv(BASE / "pleth1_pulse_morphology_v4.csv")
classified = pd.read_csv(BASE / "pleth1_pulse_morphology_v5.csv")
waveforms = pd.read_csv(BASE / "pleth1_normalized_pulses_v4.csv")
template_df = pd.read_csv(BASE / "pleth1_pulse_template_v4.csv")

# Extract data
time = filtered["time_seconds"].to_numpy()
signal = filtered["pleth_1_filtered"].to_numpy()

template = template_df["template_amplitude"].to_numpy()
normalized = waveforms.drop(columns=["pulse_number"]).to_numpy()

# Select POOR pulses for detailed inspection
poor = classified[classified["morphology_status"] == "POOR"]

print("TOTAL POOR PULSES:", len(poor))
print(poor[
    ["pulse_number", "start_time", "peak_time",
     "template_correlation", "rmse"]
].to_string(index=False))

# ------------------------------------------------
# PLOT 1: Filtered PPG signal around suspicious areas
# ------------------------------------------------

intervals = [
    (55, 70),
    (73, 89),
    (93, 109),
    (150, 160),
    (171, 181)
]

fig, axes = plt.subplots(
    len(intervals), 1,
    figsize=(15, 14)
)

for ax, (start, end) in zip(axes, intervals):
    mask = (time >= start) & (time <= end)

    ax.plot(time[mask], signal[mask])
    ax.set_title(f"Filtered PPG Signal: {start}-{end} seconds")
    ax.set_ylabel("Amplitude")
    ax.grid(True)

axes[-1].set_xlabel("Time (seconds)")

plt.tight_layout()
plt.savefig(BASE / "suspicious_signal_intervals.png", dpi=150)
plt.show()

# ------------------------------------------------
# PLOT 2: Compare POOR pulses with median template
# ------------------------------------------------

# Display up to 12 POOR pulses
good = classified[classified["morphology_status"] == "GOOD"]
selected = good.head(12)

plt.figure(figsize=(13, 7))

x = np.linspace(0, 1, len(template))

plt.plot(
    x, template,
    color="black",
    linewidth=3,
    label="Median pulse template"
)

for _, row in selected.iterrows():
    pulse_number = int(row["pulse_number"])
    waveform_row = pulse_number - 1

    pulse = normalized[waveform_row]

    plt.plot(
        x, pulse,
        alpha=0.65,
        label=f"Pulse {pulse_number}"
    )

plt.title("GOOD Pulse Morphology vs Median Template")
plt.xlabel("Normalized pulse duration")
plt.ylabel("Normalized amplitude")
plt.grid(True)
plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()

plt.savefig(BASE / "poor_pulse_comparison.png", dpi=150)
plt.show()

print("\nInspection plots saved successfully.")
