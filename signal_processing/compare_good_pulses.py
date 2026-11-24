
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("signal_processing")

# Load files
classified = pd.read_csv(BASE / "pleth1_pulse_morphology_v5.csv")
waveforms = pd.read_csv(BASE / "pleth1_normalized_pulses_v4.csv")
template_df = pd.read_csv(BASE / "pleth1_pulse_template_v4.csv")

# Select GOOD pulses
good = classified[
    classified["morphology_status"] == "GOOD"
].head(12)

# Match pulse numbers with their normalized waveforms
selected = waveforms[
    waveforms["pulse_number"].isin(good["pulse_number"])
]

template = template_df["template_amplitude"].to_numpy()
x = np.linspace(0, 1, len(template))

# Plot
plt.figure(figsize=(13, 7))

plt.plot(
    x, template,
    color="black",
    linewidth=3,
    label="Median pulse template"
)

for _, row in selected.iterrows():
    pulse_number = int(row["pulse_number"])
    pulse = row.drop("pulse_number").to_numpy(dtype=float)

    plt.plot(
        x, pulse,
        alpha=0.7,
        label=f"Pulse {pulse_number}"
    )

plt.title("GOOD Pulse Morphology vs Median Template")
plt.xlabel("Normalized pulse duration")
plt.ylabel("Normalized amplitude")
plt.grid(True)
plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()

output = BASE / "good_pulse_comparison.png"
plt.savefig(output, dpi=150)

print("Graph saved:", output)
plt.show()
