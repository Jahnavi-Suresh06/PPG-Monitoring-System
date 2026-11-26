
import { useEffect, useMemo, useRef, useState } from "react";

import {
  Activity,
  Gauge,
  Database,
  Wifi,
  WifiOff,
  Play,
  Pause,
  Square,
  RotateCcw,
  Power,
  HeartPulse,
} from "lucide-react";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const SAMPLING_FREQUENCY = 125;
const WINDOW_SECONDS = 10;
const WINDOW_SIZE = SAMPLING_FREQUENCY * WINDOW_SECONDS;

const PLAYBACK_STEP = 5;
const PLAYBACK_INTERVAL = 40;

function App() {
  const [batches, setBatches] = useState([]);
  const [waveform, setWaveform] = useState([]);
  const [waveformInfo, setWaveformInfo] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);

  const [playbackIndex, setPlaybackIndex] = useState(0);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [waveformError, setWaveformError] = useState("");
  const [analysisError, setAnalysisError] = useState("");

  const [loading, setLoading] = useState(true);
  const [waveformLoading, setWaveformLoading] = useState(true);

  const [deviceOn, setDeviceOn] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);

  const playbackSocketRef = useRef(null);

  // FETCH CURRENT RECORDING ANALYSIS
  useEffect(() => {
    let active = true;

    const fetchAnalysis = async () => {
      try {
        const response = await fetch(`${API_URL}/api/ppg/analysis`);

        if (response.status === 400) {
          // A full 32-batch recording has not arrived yet.
          if (active) {
            setAnalysisData(null);
            setAnalysisError("");
          }
          return;
        }
        if (!response.ok) {
          throw new Error(`Analysis API returned ${response.status}`);
        }

        const result = await response.json();

        if (!active) return;

        setAnalysisData(result);
        setAnalysisError("");
      } catch (err) {
        if (active) {
          setAnalysisError(err.message);
        }
      }
    };

    fetchAnalysis();

    const interval = setInterval(fetchAnalysis, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // FETCH RECEIVED BATCHES
  useEffect(() => {
    let active = true;
    let lastRecordId = 0;

    const fetchBatches = async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/ppg/batches?after_id=${lastRecordId}&limit=500`
        );

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const result = await response.json();
        const newBatches = result.batches || [];

        if (!active) return;

        setConnected(true);
        setError("");

        if (newBatches.length > 0) {
          setBatches((previous) => [...previous, ...newBatches]);

          lastRecordId = Math.max(
            lastRecordId,
            ...newBatches.map((batch) => batch.record_id)
          );
        }

        setLoading(false);
      } catch (err) {
        if (!active) return;

        setConnected(false);
        setError(err.message || "Unable to connect to server");
        setLoading(false);
      }
    };

    fetchBatches();

    const interval = setInterval(fetchBatches, 2000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // FETCH FILTERED PPG WAVEFORM
  useEffect(() => {
    let active = true;

    const fetchWaveform = async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/ppg/waveform?max_points=60000`
        );

        if (!response.ok) {
          throw new Error(`Waveform API returned ${response.status}`);
        }

        const result = await response.json();
        const receivedWaveform = result.waveform || [];

        if (!active) return;

        if (
          receivedWaveform.length > 0 &&
          receivedWaveform.some(
            (point) => typeof point.ppg_filtered !== "number"
          )
        ) {
          throw new Error("Filtered PPG data is missing");
        }

        setWaveform(receivedWaveform);
        setWaveformInfo(result);

        setPlaybackIndex(
          Math.max(
            0,
            Math.min(WINDOW_SIZE - 1, receivedWaveform.length - 1)
          )
        );

        setWaveformError("");
        setWaveformLoading(false);
      } catch (err) {
        if (!active) return;

        setWaveformError(err.message);
        setWaveformLoading(false);
      }
    };

    fetchWaveform();

    return () => {
      active = false;
    };
  }, []);

  // CONNECT TO THE SHARED BACKEND PLAYBACK CONTROLLER
  useEffect(() => {
    if (waveform.length === 0) return;

    const socket = new WebSocket("ws://127.0.0.1:8000/ws/playback");
    playbackSocketRef.current = socket;

    socket.onopen = () => {
      console.log("Client playback WebSocket connected");
      socket.send(JSON.stringify({
        action: "REGISTER",
        waveform_length: waveform.length,
      }));
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type !== "PLAYBACK_STATE") return;

        if (typeof message.playback_index === "number") {
          setPlaybackIndex(
            Math.max(0, Math.min(message.playback_index, waveform.length - 1))
          );
        }

        if (typeof message.device_on === "boolean") {
          setDeviceOn(message.device_on);
        }

        if (typeof message.is_playing === "boolean") {
          setIsPlaying(message.is_playing);
        }
      } catch (err) {
        console.error("Invalid playback state received:", err);
      }
    };

    socket.onerror = (event) => {
      console.error("Client playback WebSocket connection error:", event);
    };

    socket.onclose = (event) => {
      console.log("Client playback WebSocket closed:", event.code, event.reason);
      if (playbackSocketRef.current === socket) {
        playbackSocketRef.current = null;
      }
    };

    return () => {
      socket.close();
      if (playbackSocketRef.current === socket) {
        playbackSocketRef.current = null;
      }
    };
  }, [waveform.length]);

  // SEND PLAYBACK COMMANDS TO THE BACKEND
  const sendPlaybackCommand = (action) => {
    const socket = playbackSocketRef.current;

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action }));
    } else {
      console.warn("Playback connection is not ready yet");
    }
  };

  const handleDeviceToggle = () => sendPlaybackCommand("TOGGLE_DEVICE");
  const handlePlay = () => sendPlaybackCommand("PLAY");
  const handlePause = () => sendPlaybackCommand("PAUSE");
  const handleStop = () => sendPlaybackCommand("STOP");
  const handleReset = () => sendPlaybackCommand("RESET");

  // ROLLING WAVEFORM WINDOW
  const chartData = useMemo(() => {
    if (waveform.length === 0) return [];

    const safeIndex = Math.min(
      playbackIndex,
      waveform.length - 1
    );

    // Show the next 10-second window from the shared playback position.
    // This keeps the waveform visible at RESET (playback index 0).
    const endIndex = Math.min(waveform.length, safeIndex + WINDOW_SIZE);

    return waveform
      .slice(safeIndex, endIndex)
      .map((point) => ({
        time: point.time_seconds,
        filtered: point.ppg_filtered,
      }));
  }, [waveform, playbackIndex]);

  // DASHBOARD INFORMATION
  const latestBatch = batches.length
    ? batches[batches.length - 1]
    : null;

  const duration =
    analysisData?.recording?.duration_seconds != null
      ? analysisData.recording.duration_seconds.toFixed(2)
      : "--";

  const samplingFrequency =
    analysisData?.recording?.sampling_frequency ??
    SAMPLING_FREQUENCY;

  const totalPulses =
    analysisData?.pulse_analysis?.detected_pulses ?? "--";

  const medianHeartRate =
    analysisData?.pulse_analysis?.median_heart_rate_bpm;

  const meanHeartRate =
    analysisData?.pulse_analysis?.mean_heart_rate_bpm;

  const pulseConsistency =
    analysisData?.pulse_analysis?.pulse_consistency ?? "--";

  const sqiStatus =
    analysisData?.sqi?.status ?? "LOADING";

  const currentPlaybackTime =
    waveform[playbackIndex]?.time_seconds ?? 0;

  const playbackStatus = !deviceOn
    ? "Device OFF"
    : isPlaying
      ? "Playback running"
      : "Playback paused";

  return (
    <div className="app-shell">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Activity size={25} />
          </div>

          <div>
            <h2>PAI Edge</h2>
            <span>PPG Monitoring</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <div className="nav-item active">
          <Gauge size={19} />
          Dashboard
        </div>

        <div className="sidebar-bottom">
          <span className={`status-dot ${connected ? "online" : ""}`} />
          {connected ? "Server connected" : "Server disconnected"}
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">PATIENT MONITORING SYSTEM</p>
            <h1>PPG Dashboard</h1>
            <p className="subtitle">
              Monitor filtered PPG signals and data transmission
            </p>
          </div>

          <div className="topbar-actions">
            <button
              className={`device-toggle ${deviceOn ? "device-on" : "device-off"
                }`}
              onClick={handleDeviceToggle}
            >
              <Power size={17} />
              Device {deviceOn ? "ON" : "OFF"}
            </button>

            <div
              className={`connection ${connected ? "connected" : "disconnected"
                }`}
            >
              {connected ? <Wifi size={17} /> : <WifiOff size={17} />}
              {connected ? "API Connected" : "API Disconnected"}
            </div>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            {error}. Check that FastAPI is running on port 8000.
          </div>
        )}

        {analysisError && (
          <div className="error-banner">
            Unable to load analysis: {analysisError}
          </div>
        )}

        {/* METRIC CARDS */}
        <section className="metric-grid">
          <MetricCard
            icon={<HeartPulse />}
            label="Detected Pulses"
            value={totalPulses}
            note="Current recording"
          />

          <MetricCard
            icon={<Activity />}
            label="Signal Duration"
            value={`${duration} sec`}
            note="Calculated from sample count"
          />

          <MetricCard
            icon={<Gauge />}
            label="Sampling Frequency"
            value={`${samplingFrequency} Hz`}
            note="PPG sampling rate"
          />
        </section>

        {/* ADDITIONAL ANALYSIS */}
        <section className="metric-grid">
          <MetricCard
            icon={<HeartPulse />}
            label="Median Heart Rate"
            value={
              medianHeartRate != null
                ? `${medianHeartRate.toFixed(2)} BPM`
                : "--"
            }
            note={
              meanHeartRate != null
                ? `Mean: ${meanHeartRate.toFixed(2)} BPM`
                : "Pulse interval analysis"
            }
          />

          <MetricCard
            icon={<Activity />}
            label="Pulse Consistency"
            value={pulseConsistency}
            note="Exploratory CV thresholds"
          />

          <MetricCard
            icon={<Gauge />}
            label="SQI Status"
            value={sqiStatus}
            note="Preliminary engineering assessment"
          />
        </section>

        {/* WAVEFORM AND DETAILS */}
        <section className="content-grid">
          <div className="panel waveform-panel">
            <div className="panel-heading">
              <div>
                <h2>Filtered PPG Waveform</h2>
                <p>
                  Filtered PPG signal · Rolling 10-second window
                </p>
              </div>

              <span className="live-label">
                <span
                  className={`status-dot ${deviceOn ? "online" : ""}`}
                />
                {playbackStatus}
              </span>
            </div>

            {/* PLAYBACK CONTROLS */}
            <div className="playback-controls">
              <div className="playback-buttons">
                <button
                  className="control-button play-button"
                  onClick={handlePlay}
                  disabled={
                    !deviceOn || waveform.length === 0 || isPlaying
                  }
                  title="Play"
                >
                  <Play size={16} />
                  Play
                </button>

                <button
                  className="control-button"
                  onClick={handlePause}
                  disabled={!isPlaying}
                  title="Pause"
                >
                  <Pause size={16} />
                  Pause
                </button>

                <button
                  className="control-button"
                  onClick={handleStop}
                  disabled={waveform.length === 0}
                  title="Stop"
                >
                  <Square size={15} />
                  Stop
                </button>

                <button
                  className="control-button"
                  onClick={handleReset}
                  disabled={waveform.length === 0}
                  title="Reset"
                >
                  <RotateCcw size={16} />
                  Reset
                </button>
              </div>

              <div className="playback-time">
                {currentPlaybackTime.toFixed(2)} sec
                <span> / {duration} sec</span>
              </div>
            </div>

            {waveformError && (
              <div className="error-banner">
                Unable to load waveform: {waveformError}
              </div>
            )}

            {chartData.length > 0 ? (
              <>
                <div className="waveform-status">
                  <span className="waveform-indicator" />
                  <span>FILTERED PPG</span>

                  <span className="waveform-time">
                    Recording time: {currentPlaybackTime.toFixed(2)} sec
                  </span>
                </div>

                <div className="chart-area">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={chartData}
                      margin={{
                        top: 15,
                        right: 20,
                        left: 5,
                        bottom: 20,
                      }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#e8edf3"
                      />

                      <XAxis
                        dataKey="time"
                        type="number"
                        domain={["dataMin", "dataMax"]}
                        tick={{ fontSize: 11 }}
                        tickFormatter={(value) =>
                          Number(value).toFixed(1)
                        }
                        label={{
                          value: "Time (seconds)",
                          position: "insideBottom",
                          offset: -12,
                          fontSize: 12,
                        }}
                      />

                      <YAxis
                        tick={{ fontSize: 11 }}
                        width={55}
                        domain={["auto", "auto"]}
                        label={{
                          value: "Amplitude",
                          angle: -90,
                          position: "insideLeft",
                          fontSize: 12,
                        }}
                      />

                      <Tooltip
                        labelFormatter={(value) =>
                          `Time: ${Number(value).toFixed(3)} sec`
                        }
                        formatter={(value) => [
                          Number(value).toFixed(5),
                          "Filtered PPG",
                        ]}
                      />

                      <Line
                        type="linear"
                        dataKey="filtered"
                        name="Filtered PPG"
                        stroke="#4388D6"
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={false}
                        connectNulls={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="waveform-footer">
                  Showing {chartData.length.toLocaleString()} filtered PPG
                  samples
                  {" · "}
                  {WINDOW_SECONDS}-second moving window
                  {" · "}
                  {samplingFrequency} Hz
                </div>
              </>
            ) : (
              <div className="empty-state">
                <Activity size={38} />

                <h3>
                  {waveformLoading
                    ? "Loading filtered PPG waveform..."
                    : "No filtered waveform data available"}
                </h3>

                <p>
                  Check the waveform API and filtered signal CSV.
                </p>
              </div>
            )}
          </div>

          {/* LATEST BATCH DETAILS */}
          <div className="panel details-panel">
            <h2>Latest Batch Details</h2>

            {latestBatch ? (
              <div className="details-list">
                <Detail
                  label="Batch ID"
                  value={latestBatch.batch_id}
                />

                <Detail
                  label="Record ID"
                  value={latestBatch.record_id}
                />

                <Detail
                  label="Start Time"
                  value={`${latestBatch.start_time} sec`}
                />

                <Detail
                  label="Duration"
                  value={`${latestBatch.duration_seconds} sec`}
                />

                <Detail
                  label="Sample Count"
                  value={latestBatch.sample_count}
                />

                <Detail
                  label="Sampling Frequency"
                  value={`${latestBatch.sampling_frequency} Hz`}
                />

                <Detail
                  label="Received At"
                  value={latestBatch.received_at || "--"}
                />
              </div>
            ) : (
              <p className="muted">
                {loading
                  ? "Loading batch details..."
                  : "No batch details available."}
              </p>
            )}
          </div>
        </section>

        {/* SIGNAL QUALITY DETAILS */}
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Signal Quality Assessment</h2>
              <p>
                Preliminary engineering indicators — not clinically
                validated
              </p>
            </div>
          </div>

          {analysisData ? (
            <>
              <div className="pulse-metrics">
                <div className="pulse-metric">
                  <span>SQI Status</span>
                  <strong>{analysisData.sqi.status}</strong>
                </div>

                <div className="pulse-metric">
                  <span>Interval CV</span>
                  <strong>
                    {analysisData.pulse_analysis.interval_cv_percent != null
                      ? `${analysisData.pulse_analysis.interval_cv_percent.toFixed(2)}%`
                      : "--"}
                  </strong>
                </div>

                <div className="pulse-metric">
                  <span>Amplitude CV</span>
                  <strong>
                    {analysisData.pulse_analysis.amplitude_cv_percent != null
                      ? `${analysisData.pulse_analysis.amplitude_cv_percent.toFixed(2)}%`
                      : "--"}
                  </strong>
                </div>

                <div className="pulse-metric">
                  <span>Filtered Signal Std</span>
                  <strong>
                    {analysisData.signal_quality.filtered_std.toFixed(5)}
                  </strong>
                </div>
              </div>

              <p className="muted">
                {analysisData.sqi.message}
              </p>
            </>
          ) : (
            <p className="muted">
              {analysisError || "Loading signal quality assessment..."}
            </p>
          )}
        </section>

        {/* RECEIVED BATCH HISTORY */}
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Received Batch History</h2>
              <p>Batches received through the REST API</p>
            </div>

            <span className="batch-count-badge">
              {batches.length} records
            </span>
          </div>

          {batches.length > 0 ? (
            <div className="server-table-wrapper">
              <table className="server-table">
                <thead>
                  <tr>
                    <th>Record ID</th>
                    <th>Batch ID</th>
                    <th>Samples</th>
                    <th>Frequency</th>
                    <th>Duration</th>
                    <th>Received At</th>
                  </tr>
                </thead>

                <tbody>
                  {[...batches].slice(-10).reverse().map((batch) => (
                    <tr key={batch.record_id}>
                      <td>{batch.record_id}</td>
                      <td>{batch.batch_id}</td>
                      <td>{batch.sample_count}</td>
                      <td>{batch.sampling_frequency} Hz</td>
                      <td>{batch.duration_seconds} s</td>
                      <td>{batch.received_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">
              {loading
                ? "Loading batch history..."
                : "No batch records available."}
            </p>
          )}
        </section>

        <footer>PAI Edge · PPG Monitoring System</footer>
      </main>
    </div>
  );
}

// METRIC CARD
function MetricCard({ icon, label, value, note }) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span className="metric-icon">{icon}</span>
      </div>

      <p>{label}</p>
      <h2>{value}</h2>
      <span className="metric-note">{note}</span>
    </div>
  );
}

// DETAIL ROW
function Detail({ label, value }) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{value ?? "--"}</strong>
    </div>
  );
}

export default App;
