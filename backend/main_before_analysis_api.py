
import sqlite3
import json
import csv
import math

from pathlib import Path
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = PROJECT_ROOT / "ppg_monitoring.db"

WAVEFORM_PATH = (
    PROJECT_ROOT
    / "signal_processing"
    / "received_ppg_filtered.csv"
)

transmission_completed = False


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="PPG Monitoring System API",
    description="REST API for PPG waveform transmission and monitoring",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://10.104.202.164:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# DATA MODEL
# --------------------------------------------------

class PPGBatch(BaseModel):
    batch_id: int
    start_time: float
    sampling_frequency: int
    duration_seconds: int
    sample_count: int
    samples: List[float]


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS ppg_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            start_time REAL NOT NULL,
            sampling_frequency INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL,
            sample_count INTEGER NOT NULL,
            samples_json TEXT NOT NULL,
            received_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


@app.on_event("startup")
def startup_event():
    initialize_database()


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "PPG Monitoring System API is running",
        "status": "success"
    }


# --------------------------------------------------
# TRANSMISSION STATUS
# --------------------------------------------------

@app.get("/api/ppg/status")
def get_transmission_status():

    return {
        "transmission_completed": transmission_completed
    }


@app.post("/api/ppg/complete")
def complete_transmission():

    global transmission_completed

    transmission_completed = True

    return {
        "message": "PPG transmission completed",
        "transmission_completed": True
    }


# --------------------------------------------------
# RECEIVE PPG BATCH
# --------------------------------------------------

@app.post("/api/ppg/batch")
def receive_ppg_batch(batch: PPGBatch):

    if batch.sampling_frequency != 125:
        raise HTTPException(
            status_code=400,
            detail="Invalid sampling frequency"
        )

    if batch.sample_count != len(batch.samples):
        raise HTTPException(
            status_code=400,
            detail="Sample count mismatch"
        )

    if batch.sample_count != 250:
        raise HTTPException(
            status_code=400,
            detail="Expected 250 samples per batch"
        )

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO ppg_batches (
            batch_id,
            start_time,
            sampling_frequency,
            duration_seconds,
            sample_count,
            samples_json,
            received_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            batch.batch_id,
            batch.start_time,
            batch.sampling_frequency,
            batch.duration_seconds,
            batch.sample_count,
            json.dumps(batch.samples),
            datetime.now(timezone.utc).isoformat()
        )
    )

    connection.commit()

    record_id = cursor.lastrowid

    connection.close()

    return {
        "message": "PPG batch received and stored successfully",
        "status": "success",
        "record_id": record_id,
        "batch_id": batch.batch_id,
        "start_time": batch.start_time,
        "sampling_frequency": batch.sampling_frequency,
        "samples_received": batch.sample_count,
        "samples": batch.samples[:10]
    }


# --------------------------------------------------
# GET RECEIVED BATCHES
# --------------------------------------------------

@app.get("/api/ppg/batches")
def get_ppg_batches(
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=500)
):

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT * FROM ppg_batches
        WHERE id > ?
        ORDER BY id ASC
        LIMIT ?
        """,
        (after_id, limit)
    ).fetchall()

    connection.close()

    return {
        "total_returned": len(rows),

        "batches": [
            {
                "record_id": row["id"],
                "batch_id": row["batch_id"],
                "start_time": row["start_time"],
                "sampling_frequency": row["sampling_frequency"],
                "duration_seconds": row["duration_seconds"],
                "sample_count": row["sample_count"],
                "samples": json.loads(row["samples_json"]),
                "received_at": row["received_at"]
            }
            for row in rows
        ]
    }


# --------------------------------------------------
# GET LATEST BATCH
# --------------------------------------------------

@app.get("/api/ppg/latest")
def get_latest_ppg_batch():

    connection = get_connection()

    row = connection.execute(
        """
        SELECT * FROM ppg_batches
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    connection.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="No PPG batches found"
        )

    return {
        "record_id": row["id"],
        "batch_id": row["batch_id"],
        "start_time": row["start_time"],
        "sampling_frequency": row["sampling_frequency"],
        "duration_seconds": row["duration_seconds"],
        "sample_count": row["sample_count"],
        "samples": json.loads(row["samples_json"]),
        "received_at": row["received_at"]
    }


# --------------------------------------------------
# GET RAW AND FILTERED PPG WAVEFORM
# --------------------------------------------------

@app.get("/api/ppg/waveform")
def get_complete_waveform(
    start_time: float = Query(default=0, ge=0),
    end_time: float = Query(default=480, gt=0),
    max_points: int = Query(default=60000, ge=100, le=60000)
):

    if start_time >= end_time:
        raise HTTPException(
            status_code=400,
            detail="start_time must be smaller than end_time"
        )

    if not WAVEFORM_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed PPG waveform CSV not found"
        )

    points = []

    try:

        with open(
            WAVEFORM_PATH,
            "r",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            required_columns = {
                "time_seconds",
                "ppg_raw",
                "ppg_filtered"
            }

            if (
                not reader.fieldnames
                or not required_columns.issubset(set(reader.fieldnames))
            ):
                raise HTTPException(
                    status_code=500,
                    detail="CSV must contain time_seconds, ppg_raw and ppg_filtered"
                )

            for row in reader:

                timestamp = float(row["time_seconds"])

                if start_time <= timestamp <= end_time:

                    points.append({
                        "time_seconds": timestamp,
                        "ppg_raw": float(row["ppg_raw"]),
                        "ppg_filtered": float(row["ppg_filtered"])
                    })

    except HTTPException:
        raise

    except (KeyError, ValueError, OSError) as error:

        raise HTTPException(
            status_code=500,
            detail=f"Error reading waveform CSV: {error}"
        )

    if not points:

        raise HTTPException(
            status_code=404,
            detail="No waveform samples found in the requested time range"
        )

    original_count = len(points)

    last_point = points[-1]

    if original_count > max_points:

        step = math.ceil(original_count / max_points)

        points = points[::step]

        if points[-1]["time_seconds"] != last_point["time_seconds"]:
            points.append(last_point)

    return {
        "sampling_frequency": 125,
        "total_samples": original_count,
        "returned_samples": len(points),
        "start_time": points[0]["time_seconds"],
        "end_time": points[-1]["time_seconds"],
        "waveform": points
    }
