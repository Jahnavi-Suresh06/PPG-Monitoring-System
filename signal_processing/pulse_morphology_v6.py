
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("signal_processing")

# Load Version 4 and Version 5 results
pulse_df = pd.read_csv(BASE / "pleth1_pulse_morphology_v4.csv")
waveform_df = pd.read_csv(BASE / "pleth1_normalized_pulses_v4.csv")

# Sort and match pulses using pulse_number
pulse_df = pulse_df.sort_values("pulse_number").reset_index(drop=True)
waveform_df = waveform_df.sort_values("pulse_number").reset_index(drop=True)

if not np.array_equal(
    pulse_df["pulse_number"].to_numpy(),
    waveform_df["pulse_number"].to_numpy()
):
    raise ValueError("Pulse numbers do not match.")

waveforms = waveform_df.drop(columns=["pulse_number"]).to_numpy(dtype=float)

# Load global median template
template_df = pd.read_csv(BASE / "pleth1_pulse_template_v4.csv")
global_template = template_df["template_amplitude"].to_numpy()

# Calculate global RMSE
global_rmse = np.sqrt(
    np.mean((waveforms - global_template) ** 2, axis=1)
)

pulse_df["rmse"] = global_rmse

total_pulses = len(waveforms)

# Local template settings
NEIGHBOR_RADIUS = 10

local_correlations = []
local_rmses = []

# Calculate local template for every pulse
for i in range(total_pulses):

    start = max(0, i - NEIGHBOR_RADIUS)
    end = min(total_pulses, i + NEIGHBOR_RADIUS + 1)

    # Use nearby pulses, excluding the current pulse
    neighbor_indices = [
        j for j in range(start, end) if j != i
    ]

    neighbors = waveforms[neighbor_indices]

    # Local median template
    local_template = np.median(neighbors, axis=0)

    current_pulse = waveforms[i]

    # Local RMSE
    rmse = np.sqrt(
        np.mean((current_pulse - local_template) ** 2)
    )

    # Local Pearson correlation
    if (
        np.std(current_pulse) == 0
        or np.std(local_template) == 0
    ):
        correlation = np.nan
    else:
        correlation = np.corrcoef(
            current_pulse, local_template
        )[0, 1]

    local_correlations.append(correlation)
    local_rmses.append(rmse)

# Add local measurements
pulse_df["local_template_correlation"] = local_correlations
pulse_df["local_template_rmse"] = local_rmses

# Save results
output_csv = BASE / "pleth1_pulse_morphology_v6.csv"
pulse_df.to_csv(output_csv, index=False)

# Print overall comparison
print("\nPPG MORPHOLOGY VERSION 6")
print("------------------------")

print("Total pulses:", total_pulses)

print("\nGLOBAL TEMPLATE METRICS:")
print(pulse_df[
    ["template_correlation", "rmse"]
].describe().round(4))

print("\nLOCAL TEMPLATE METRICS:")
print(pulse_df[
    ["local_template_correlation", "local_template_rmse"]
].describe().round(4))

# Compare the important 73-110 second interval
interval = pulse_df[
    (pulse_df["start_time"] >= 73) &
    (pulse_df["start_time"] <= 110)
]

print("\n73-110 SECOND INTERVAL:")
print(interval[
    [
        "pulse_number",
        "start_time",
        "template_correlation",
        "local_template_correlation",
        "rmse",
        "local_template_rmse"
    ]
].round(4).to_string(index=False))

# Plot correlation comparison
plt.figure(figsize=(14, 6))

plt.plot(
    pulse_df["peak_time"],
    pulse_df["template_correlation"],
    label="Global template correlation",
    alpha=0.7
)

plt.plot(
    pulse_df["peak_time"],
    pulse_df["local_template_correlation"],
    label="Local template correlation",
    alpha=0.8
)

plt.xlabel("Time (seconds)")
plt.ylabel("Correlation")
plt.title("Global vs Local Pulse Morphology Correlation")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(BASE / "global_vs_local_correlation_v6.png", dpi=150)
plt.show()

# Plot RMSE comparison
plt.figure(figsize=(14, 6))

plt.plot(
    pulse_df["peak_time"],
    pulse_df["rmse"],
    label="Global template RMSE",
    alpha=0.7
)

plt.plot(
    pulse_df["peak_time"],
    pulse_df["local_template_rmse"],
    label="Local template RMSE",
    alpha=0.8
)

plt.xlabel("Time (seconds)")
plt.ylabel("RMSE")
plt.title("Global vs Local Pulse Morphology RMSE")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(BASE / "global_vs_local_rmse_v6.png", dpi=150)
plt.show()

print("\nVersion 6 completed.")
print("Saved:", output_csv)
print("Saved: global_vs_local_correlation_v6.png")
print("Saved: global_vs_local_rmse_v6.png")
