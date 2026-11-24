
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.signal import find_peaks
from pathlib import Path

# ==========================================
# 1. CONFIGURATION
# ==========================================

INPUT_FILE = "signal_processing/pleth1_filtered.csv"
OUTPUT_DIR = Path("signal_processing")

FS = 500
MIN_PULSE_INTERVAL_SEC = 0.30
RESAMPLED_POINTS = 100

# Exploratory peak detection setting.
# We will inspect detection performance before tuning.
PROMINENCE_FACTOR = 0.10

# ==========================================
# 2. LOAD FILTERED PPG SIGNAL
# ==========================================

df = pd.read_csv(INPUT_FILE)

time = df["time_seconds"].to_numpy(dtype=float)
signal = df["pleth_1_filtered"].to_numpy(dtype=float)

if len(signal) != len(time):
    raise ValueError("Signal and time arrays have different lengths.")

if len(signal) < FS * 10:
    raise ValueError("Not enough data for morphology analysis.")

print("PPG PULSE MORPHOLOGY - VERSION 4")
print("--------------------------------")
print("Sampling frequency:", FS, "Hz")
print("Total samples:", len(signal))
print("Duration:", round(time[-1] - time[0], 2), "seconds")

# ==========================================
# 3. DETECT SYSTOLIC PEAKS
# ==========================================

min_distance = int(MIN_PULSE_INTERVAL_SEC * FS)

prominence = PROMINENCE_FACTOR * np.std(signal)

peaks, peak_properties = find_peaks(
    signal,
    distance=min_distance,
    prominence=prominence
)

print("\nDetected systolic peaks:", len(peaks))

# ==========================================
# 4. DETECT PULSE VALLEYS
# ==========================================

valleys, valley_properties = find_peaks(
    -signal,
    distance=min_distance,
    prominence=prominence
)

print("Detected valleys:", len(valleys))

# ==========================================
# 5. EXTRACT TROUGH-TO-TROUGH PULSES
# ==========================================

pulse_waveforms = []
pulse_records = []

for i in range(len(valleys) - 1):

    start_idx = valleys[i]
    end_idx = valleys[i + 1]

    # Find systolic peaks between consecutive valleys
    peaks_inside = peaks[
        (peaks > start_idx) &
        (peaks < end_idx)
    ]

    # Accept only cycles with exactly one systolic peak
    if len(peaks_inside) != 1:
        continue

    peak_idx = peaks_inside[0]

    cycle = signal[start_idx:end_idx + 1]

    if len(cycle) < 10:
        continue

    baseline = signal[start_idx]
    amplitude = signal[peak_idx] - baseline

    if amplitude <= 0:
        continue

    # Normalize amplitude while preserving waveform shape
    normalized_cycle = (cycle - baseline) / amplitude

    # Normalize each pulse to a common number of time points
    original_positions = np.linspace(
        0, 1, len(normalized_cycle)
    )

    target_positions = np.linspace(
        0, 1, RESAMPLED_POINTS
    )

    resampled_cycle = np.interp(
        target_positions,
        original_positions,
        normalized_cycle
    )

    pulse_waveforms.append(resampled_cycle)

    pulse_records.append({
        "pulse_number": len(pulse_records) + 1,
        "start_time": time[start_idx],
        "peak_time": time[peak_idx],
        "end_time": time[end_idx],
        "interval_seconds": time[end_idx] - time[start_idx],
        "amplitude": amplitude,
        "duration_seconds": time[end_idx] - time[start_idx]
    })

if len(pulse_waveforms) < 5:
    raise ValueError(
        "Too few valid pulses extracted. "
        "Inspect peak and valley detection settings."
    )

pulse_waveforms = np.asarray(pulse_waveforms)

pulse_df = pd.DataFrame(pulse_records)

print("Valid extracted pulses:", len(pulse_waveforms))

# ==========================================
# 6. CREATE REPRESENTATIVE PULSE TEMPLATE
# ==========================================

# Median waveform reduces the influence of unusual pulses
template = np.median(pulse_waveforms, axis=0)

# ==========================================
# 7. CALCULATE MORPHOLOGY CORRELATION
# ==========================================

correlations = []

for waveform in pulse_waveforms:

    if np.std(waveform) == 0 or np.std(template) == 0:
        correlation = np.nan
    else:
        correlation = np.corrcoef(
            waveform,
            template
        )[0, 1]

    correlations.append(correlation)

pulse_df["template_correlation"] = correlations

# ==========================================
# 8. SAVE PULSE-LEVEL RESULTS
# ==========================================

pulse_df.to_csv(
    OUTPUT_DIR / "pleth1_pulse_morphology_v4.csv",
    index=False
)

# Save the normalized pulse waveforms
waveform_columns = [
    f"point_{i + 1}"
    for i in range(RESAMPLED_POINTS)
]

waveform_df = pd.DataFrame(
    pulse_waveforms,
    columns=waveform_columns
)

waveform_df.insert(
    0,
    "pulse_number",
    pulse_df["pulse_number"]
)

waveform_df.to_csv(
    OUTPUT_DIR / "pleth1_normalized_pulses_v4.csv",
    index=False
)

# Save representative template
pd.DataFrame({
    "normalized_position": np.linspace(
        0, 1, RESAMPLED_POINTS
    ),
    "template_amplitude": template
}).to_csv(
    OUTPUT_DIR / "pleth1_pulse_template_v4.csv",
    index=False
)

# ==========================================
# 9. PRINT SUMMARY
# ==========================================

print("\nMORPHOLOGY SUMMARY")
print("------------------")

print("Valid pulses:", len(pulse_df))

print("\nPulse interval statistics:")
print(pulse_df["interval_seconds"].describe())

print("\nPulse amplitude statistics:")
print(pulse_df["amplitude"].describe())

print("\nTemplate correlation statistics:")
print(pulse_df["template_correlation"].describe())

print("\nLowest 10 correlations:")

print(
    pulse_df.nsmallest(
        10, "template_correlation"
    )[
        [
            "pulse_number",
            "start_time",
            "peak_time",
            "amplitude",
            "template_correlation"
        ]
    ].to_string(index=False)
)

# ==========================================
# 10. PLOT INDIVIDUAL PULSES AND TEMPLATE
# ==========================================

plt.figure(figsize=(14, 6))

for i in range(min(30, len(pulse_waveforms))):
    plt.plot(
        np.linspace(0, 100, RESAMPLED_POINTS),
        pulse_waveforms[i],
        alpha=0.20,
        linewidth=0.8
    )

plt.plot(
    np.linspace(0, 100, RESAMPLED_POINTS),
    template,
    color="black",
    linewidth=3,
    label="Median pulse template"
)

plt.xlabel("Normalized pulse duration (%)")
plt.ylabel("Normalized amplitude")
plt.title("PPG Individual Pulse Morphology")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "pleth1_morphology_v4.png",
    dpi=150
)

plt.show()

# ==========================================
# 11. PLOT TEMPLATE CORRELATION
# ==========================================

plt.figure(figsize=(14, 5))

plt.plot(
    pulse_df["peak_time"],
    pulse_df["template_correlation"],
    marker=".",
    linewidth=1
)

plt.axhline(
    pulse_df["template_correlation"].median(),
    linestyle="--",
    label="Median correlation"
)

plt.xlabel("Time (seconds)")
plt.ylabel("Correlation")
plt.title("PPG Pulse Morphology Correlation")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "pleth1_correlation_v4.png",
    dpi=150
)

plt.show()

print("\nVersion 4 completed successfully.")

print("\nGenerated files:")
print("- pleth1_pulse_morphology_v4.csv")
print("- pleth1_normalized_pulses_v4.csv")
print("- pleth1_pulse_template_v4.csv")
print("- pleth1_morphology_v4.png")
print("- pleth1_correlation_v4.png")
