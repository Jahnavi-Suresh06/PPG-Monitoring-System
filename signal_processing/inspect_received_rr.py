
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("signal_processing")

df = pd.read_csv(BASE / "received_pulse_detection.csv")

peaks = df[
    df["is_systolic_peak"].astype(str).str.lower() == "true"
].copy()

peak_times = peaks["time_seconds"].to_numpy()

intervals = np.diff(peak_times)
heart_rates = 60 / intervals

rr_df = pd.DataFrame({
    "previous_peak_time": peak_times[:-1],
    "current_peak_time": peak_times[1:],
    "interval_seconds": intervals,
    "heart_rate_bpm": heart_rates
})

print("\nRR INTERVAL VALIDATION")
print("----------------------")

print("Total detected peaks:", len(peak_times))
print("Total RR intervals:", len(intervals))

print("\nRR INTERVAL STATISTICS:")
print(rr_df["interval_seconds"].describe().round(4))

print("\nHEART RATE STATISTICS:")
print(rr_df["heart_rate_bpm"].describe().round(2))

# Flag unusual values for manual inspection.
# These are review thresholds, not clinical limits.
unusual = rr_df[
    (rr_df["heart_rate_bpm"] < 50) |
    (rr_df["heart_rate_bpm"] > 150)
]

print("\nUNUSUAL HEART RATE INTERVALS:")
print("Count:", len(unusual))

if len(unusual):
    print(unusual.round(3).to_string(index=False))
else:
    print("No intervals flagged.")

rr_df.to_csv(
    BASE / "received_rr_intervals.csv",
    index=False
)

print("\nSaved: received_rr_intervals.csv")
