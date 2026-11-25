
import { useEffect, useMemo, useState } from "react";

import {
  Activity,
  HeartPulse,
  Gauge,
  Database,
  Wifi,
  WifiOff,
  RefreshCw,
  Waves,
  Play,
  Pause,
  Square,
  RotateCcw,
  Power,
} from "lucide-react";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";

import "./App.css";

const API_URL = "http://10.104.202.164:8000";

const SAMPLING_FREQUENCY = 125;
const WINDOW_SECONDS = 10;
const WINDOW_SIZE = SAMPLING_FREQUENCY * WINDOW_SECONDS;

const PLAYBACK_STEP = 5;
const PLAYBACK_INTERVAL = 40;

function App() {
  const [batches, setBatches] = useState([]);
  const [waveform, setWaveform] = useState([]);
  const [playbackIndex, setPlaybackIndex] = useState(0);
  const [waveformInfo, setWaveformInfo] = useState(null);

  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [waveformError, setWaveformError] = useState("");

  const [loading, setLoading] = useState(true);
  const [waveformLoading, setWaveformLoading] = useState(true);

  const [deviceOn, setDeviceOn] = useState(true);
  const [isPlaying, setIsPlaying] = useState(true);

  // FETCH RECEIVED BATCHES

  useEffect(() => {
    let active = true;
    let lastRecordId = 0;

    const fetchBatches = async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/ppg/batches?after_id=${lastRecordId}&limit=20`
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

  // FETCH COMPLETE PPG WAVEFORM

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
          (
            typeof receivedWaveform[0].ppg_raw !== "number" ||
            typeof receivedWaveform[0].ppg_filtered !== "number"
          )
        ) {
          throw new Error("Raw or filtered PPG data is missing from API response");
        }

        setWaveform(receivedWaveform);
        setWaveformInfo(result);

        setPlaybackIndex(
          Math.min(WINDOW_SIZE - 1, receivedWaveform.length - 1)
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

  // CONTINUOUS RECORDED WAVEFORM PLAYBACK

  useEffect(() => {
    if (!deviceOn || !isPlaying || waveform.length === 0) {
      return;
    }

    const interval = setInterval(() => {
      setPlaybackIndex((previousIndex) => {
        return (previousIndex + PLAYBACK_STEP) % waveform.length;
      });
    }, PLAYBACK_INTERVAL);

    return () => clearInterval(interval);
  }, [deviceOn, isPlaying, waveform.length]);

  // PLAYBACK CONTROLS

  const handleDeviceToggle = () => {
    if (deviceOn) {
      setDeviceOn(false);
      setIsPlaying(false);
    } else {
      setDeviceOn(true);
    }
  };

  const handlePlay = () => {
    if (deviceOn && waveform.length > 0) {
      setIsPlaying(true);
    }
  };

  const handlePause = () => {
    setIsPlaying(false);
  };

  const handleStop = () => {
    setIsPlaying(false);
    setPlaybackIndex(
      Math.min(WINDOW_SIZE - 1, waveform.length - 1)
    );
  };

  const handleReset = () => {
    setIsPlaying(false);
    setPlaybackIndex(0);
  };

  // CREATE ROLLING 10-SECOND CHART WINDOW

  const chartData = useMemo(() => {
    if (waveform.length === 0) return [];

    const startIndex = Math.max(
      0,
      playbackIndex - WINDOW_SIZE + 1
    );

    const visibleSamples = waveform.slice(
      startIndex,
      playbackIndex + 1
    );

    return visibleSamples.map((point, index) => ({
      time: index / SAMPLING_FREQUENCY,
      raw: point.ppg_raw,
      filtered: point.ppg_filtered,
    }));
  }, [waveform, playbackIndex]);

  // DASHBOARD INFORMATION

  const latestBatch = batches.length
    ? batches[batches.length - 1]
    : null;

  const totalSamples = waveformInfo?.total_samples || 0;

  const duration =
    waveformInfo?.end_time != null
      ? (
        waveformInfo.end_time - waveformInfo.start_time
      ).toFixed(1)
      : "0";

  const samplingFrequency =
    waveformInfo?.sampling_frequency || SAMPLING_FREQUENCY;

  const currentPlaybackTime =
    waveform[playbackIndex]?.time_seconds ?? 0;

  const playbackStatus = !deviceOn
    ? "Device OFF"
    : isPlaying
      ? "Playback running"
      : "Playback paused";

  // FRONTEND

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

        <div className="nav-item">
          <Waves size={19} />
          Signal Monitoring
        </div>

        <div className="nav-item">
          <Database size={19} />
          Data Batches
        </div>

        <div className="sidebar-bottom">
          <span className={`status-dot ${connected ? "online" : ""}`} />
          {connected ? "Server connected" : "Server disconnected"}
        </div>
      </aside>

      {/* MAIN CONTENT */}

      <main className="main-content">

        {/* HEADER */}

        <header className="topbar">
          <div>
            <p className="eyebrow">PATIENT MONITORING SYSTEM</p>

            <h1>PPG Dashboard</h1>

            <p className="subtitle">
              Monitor PPG signals, waveform processing and data transmission
            </p>
          </div>

          <div className="topbar-actions">
            <button
              className={`device-toggle ${deviceOn ? "device-on" : "device-off"}`}
              onClick={handleDeviceToggle}
            >
              <Power size={17} />
              Device {deviceOn ? "ON" : "OFF"}
            </button>

            <div className={`connection ${connected ? "connected" : "disconnected"}`}>
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

        {/* METRIC CARDS */}

        <section className="metric-grid">
          <MetricCard
            icon={<Database />}
            label="Total Samples"
            value={totalSamples.toLocaleString()}
            note="Samples in complete PPG signal"
          />

          <MetricCard
            icon={<Activity />}
            label="Signal Duration"
            value={`${duration} sec`}
            note="Complete recorded waveform"
          />

          <MetricCard
            icon={<Gauge />}
            label="Sampling Frequency"
            value={`${samplingFrequency} Hz`}
            note="PPG signal sampling rate"
          />

          <MetricCard
            icon={<HeartPulse />}
            label="Signal Quality (SQI)"
            value="Pending"
            note="Awaiting validated SQI calculation"
          />
        </section>

        {/* WAVEFORM AND DETAILS */}

        <section className="content-grid">

          {/* PPG WAVEFORM */}

          <div className="panel waveform-panel">

            <div className="panel-heading">
              <div>
                <h2>PPG Waveform Monitoring</h2>
                <p>Raw and Filtered PPG signals · Rolling 10-second window</p>
              </div>

              <span className="live-label">
                <span className={`status-dot ${deviceOn ? "online" : ""}`} />
                {playbackStatus}
              </span>
            </div>

            {/* PLAYBACK CONTROLS */}

            <div className="playback-controls">

              <div className="playback-buttons">
                <button
                  className="control-button play-button"
                  onClick={handlePlay}
                  disabled={!deviceOn || waveform.length === 0 || isPlaying}
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
                  <span>RAW + FILTERED PPG</span>

                  <span className="waveform-time">
                    Recording time: {currentPlaybackTime.toFixed(2)} sec
                  </span>
                </div>

                {/* PPG CHART */}

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
                        domain={[0, WINDOW_SECONDS]}
                        tick={{ fontSize: 11 }}
                        tickFormatter={(value) => value.toFixed(0)}
                        allowDataOverflow={true}
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

                      <Legend
                        verticalAlign="top"
                        height={36}
                      />

                      <Tooltip
                        labelFormatter={(value) =>
                          `Time: ${Number(value).toFixed(2)} sec`
                        }
                        formatter={(value, name) => [
                          Number(value).toFixed(5),
                          name,
                        ]}
                      />

                      {/* RAW PPG LINE */}

                      <Line
                        type="linear"
                        dataKey="raw"
                        name="Raw PPG"
                        stroke="#16856b"
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={false}
                        connectNulls={false}
                      />

                      {/* FILTERED PPG LINE */}

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
                  Showing {chartData.length.toLocaleString()} raw and filtered samples
                  {" · "}
                  {WINDOW_SECONDS}-second moving window
                  {" · "}
                  {SAMPLING_FREQUENCY} Hz
                </div>
              </>
            ) : (
              <div className="empty-state">
                <Activity size={38} />

                <h3>
                  {waveformLoading
                    ? "Loading PPG waveform..."
                    : "No waveform data available"}
                </h3>

                <p>
                  Check the waveform API and processed signal CSV.
                </p>
              </div>
            )}
          </div>

          {/* LATEST BATCH DETAILS */}

          <div className="panel details-panel">
            <h2>Latest Batch Details</h2>

            {latestBatch ? (
              <div className="details-list">
                <Detail label="Batch ID" value={latestBatch.batch_id} />

                <Detail label="Record ID" value={latestBatch.record_id} />

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

        {/* BATCH HISTORY */}

        <section className="panel table-panel">
          <div className="panel-heading">
            <div>
              <h2>Received Batch History</h2>
              <p>Data retrieved from the FastAPI backend</p>
            </div>

            <button
              className="refresh-button"
              onClick={() => window.location.reload()}
            >
              <RefreshCw size={15} />
              Refresh
            </button>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Record ID</th>
                  <th>Batch ID</th>
                  <th>Start Time</th>
                  <th>Duration</th>
                  <th>Samples</th>
                  <th>Frequency</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {[...batches].reverse().slice(0, 10).map((batch) => (
                  <tr key={batch.record_id}>
                    <td>#{batch.record_id}</td>
                    <td>{batch.batch_id}</td>
                    <td>{batch.start_time} sec</td>
                    <td>{batch.duration_seconds} sec</td>
                    <td>{batch.sample_count}</td>
                    <td>{batch.sampling_frequency} Hz</td>

                    <td>
                      <span className="received-badge">
                        Received
                      </span>
                    </td>
                  </tr>
                ))}

                {batches.length === 0 && (
                  <tr>
                    <td colSpan="7" className="empty-table">
                      No batches received yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <footer>
          PAI Edge · PPG Monitoring System · Batch refresh every 2 seconds
        </footer>
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
      <strong>{value}</strong>
    </div>
  );
}

export default App;
