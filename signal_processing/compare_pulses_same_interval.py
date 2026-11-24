
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("signal_processing")

classified = pd.read_csv(BASE / "pleth1_pulse_morphology_v5.csv")
waveforms = pd.read_csv(BASE / "pleth1_normalized_pulses_v4.csv")
template_df = pd.read_csv(BASE / "pleth1_pulse_template_v4.csv")

# Select pulses from the same time interval
window = classified[
    (classified["start_time"] >= 73) &
    (classified["start_time"] <= 110)
].copy()

good = window[window["morphology_status"] == "GOOD"]
poor = window[window["morphology_status"] == "POOR"]

print("GOOD pulses in interval:", len(good))
print("POOR pulses in interval:", len(poor))

# Select up to 6 from each group
selected = pd.concat([
    good.head(6),
    poor.head(6)
])

template = template_df["template_amplitude"].to_numpy()
x = np.linspace(0, 1, len(template))

plt.figure(figsize=(12, 7))

plt.plot(
    x, template,
    color="black",
    linewidth=3,
    label="Global median template"
)

for _, row in selected.iterrows():
    pulse_number = int(row["pulse_number"])

    pulse_row = waveforms[
        waveforms["pulse_number"] == pulse_number
    ].iloc[0]

    pulse = pulse_row.drop("pulse_number").to_numpy(dtype=float)

    status = row["morphology_status"]

    plt.plot(
        x, pulse,
        linewidth=1.5,
        label=f"{status} - Pulse {pulse_number}"
    )

plt.title("GOOD vs POOR Pulses: Same Time Interval (73-110 sec)")
plt.xlabel("Normalized pulse duration")
plt.ylabel("Normalized amplitude")
plt.grid(True)
plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()

plt.savefig(BASE / "same_interval_pulse_comparison.png", dpi=150)
plt.show()
