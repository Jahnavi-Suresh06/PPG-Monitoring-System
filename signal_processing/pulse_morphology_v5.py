
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("signal_processing")

# Load Version 4 outputs
pulse_df = pd.read_csv(BASE / "pleth1_pulse_morphology_v4.csv")
waveform_df = pd.read_csv(BASE / "pleth1_normalized_pulses_v4.csv")
template_df = pd.read_csv(BASE / "pleth1_pulse_template_v4.csv")

template = template_df["template_amplitude"].to_numpy()
waveforms = waveform_df.drop(columns=["pulse_number"]).to_numpy()

if len(pulse_df) != len(waveforms):
    raise ValueError("Pulse records and waveforms do not match.")

if waveforms.shape[1] != len(template):
    raise ValueError("Waveform and template dimensions do not match.")

# Calculate RMSE for every pulse
rmse = np.sqrt(np.mean((waveforms - template) ** 2, axis=1))
pulse_df["rmse"] = rmse

# Initial exploratory classification thresholds
GOOD_CORR = 0.90
GOOD_RMSE = 0.10

POOR_CORR = 0.80
POOR_RMSE = 0.15


def classify(row):
    corr = row["template_correlation"]
    error = row["rmse"]

    if pd.isna(corr) or pd.isna(error):
        return "REVIEW"

    if corr < POOR_CORR and error > POOR_RMSE:
        return "POOR"

    if corr < GOOD_CORR or error > GOOD_RMSE:
        return "SUSPICIOUS"

    return "GOOD"


pulse_df["morphology_status"] = pulse_df.apply(classify, axis=1)

# Save complete pulse-level report
output_csv = BASE / "pleth1_pulse_morphology_v5.csv"
pulse_df.to_csv(output_csv, index=False)

print("PPG MORPHOLOGY VERSION 5")
print("------------------------")
print("Total pulses:", len(pulse_df))

print("\nCLASSIFICATION:")
print(pulse_df["morphology_status"].value_counts().to_string())

print("\nPERCENTAGES:")
print(
    (pulse_df["morphology_status"].value_counts(normalize=True) * 100)
    .round(2).to_string()
)

print("\nLOWEST CORRELATION PULSES:")
print(
    pulse_df.nsmallest(15, "template_correlation")[
        ["pulse_number", "start_time", "template_correlation",
         "rmse", "morphology_status"]
    ].to_string(index=False)
)

print("\nHIGHEST RMSE PULSES:")
print(
    pulse_df.nlargest(15, "rmse")[
        ["pulse_number", "start_time", "template_correlation",
         "rmse", "morphology_status"]
    ].to_string(index=False)
)

# Plot correlation and RMSE over time
fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)

axes[0].plot(
    pulse_df["peak_time"],
    pulse_df["template_correlation"],
    marker=".",
    linewidth=1
)
axes[0].axhline(GOOD_CORR, linestyle="--", label="Good threshold")
axes[0].set_ylabel("Template correlation")
axes[0].set_title("Pulse Morphology Correlation")
axes[0].grid(True)
axes[0].legend()

axes[1].plot(
    pulse_df["peak_time"],
    pulse_df["rmse"],
    marker=".",
    linewidth=1
)
axes[1].axhline(GOOD_RMSE, linestyle="--", label="Good threshold")
axes[1].set_xlabel("Time (seconds)")
axes[1].set_ylabel("RMSE")
axes[1].set_title("Pulse Morphology RMSE")
axes[1].grid(True)
axes[1].legend()

plt.tight_layout()
plt.savefig(BASE / "pleth1_morphology_v5_review.png", dpi=150)
plt.show()

# Plot correlation versus RMSE
plt.figure(figsize=(9, 6))
plt.scatter(
    pulse_df["template_correlation"],
    pulse_df["rmse"],
    alpha=0.6
)
plt.axvline(GOOD_CORR, linestyle="--", label="Correlation threshold")
plt.axhline(GOOD_RMSE, linestyle="--", label="RMSE threshold")
plt.xlabel("Template correlation")
plt.ylabel("RMSE")
plt.title("Correlation vs RMSE - PPG Pulse Morphology")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(BASE / "pleth1_morphology_v5_scatter.png", dpi=150)
plt.show()

print("\nVersion 5 completed.")
print("Saved:", output_csv)
print("Saved: pleth1_morphology_v5_review.png")
print("Saved: pleth1_morphology_v5_scatter.png")
