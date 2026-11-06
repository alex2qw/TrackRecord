import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const initialFilters = {
  journey_leg: "", station: "", operator: "", event_type: "", from_date: "", to_date: "",
};

const formatPercent = value => value == null ? "—" : `${Number(value).toFixed(1)}%`;
const formatMinutes = value => value == null ? "—" : `${Number(value).toFixed(1)} min`;
const formatPeriod = period => !period?.from || !period?.to ? "—" : period.from === period.to ? period.from : `${period.from} → ${period.to}`;

async function getJson(path) {
  const response = await fetch(path);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "API request failed.");
  return body;
}

function queryString(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
  return params.toString();
}

function BarList({ items, formatter = formatPercent }) {
  if (!items.length) return <p className="muted">No grouped observations available.</p>;
  return <div className="bars">{items.map(item => (
    <div className="bar-row" key={item.label}>
      <span>{item.label}</span>
      <div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, item.value ?? 0))}%` }} /></div>
      <strong>{formatter(item.value)}</strong>
    </div>
  ))}</div>;
}

function Filters({ filters, options, onChange, onSubmit, onReset }) {
  const field = (name, label, values, placeholder) => <label>{label}
    <select value={filters[name]} onChange={event => onChange(name, event.target.value)}>
      <option value="">{placeholder}</option>{values.map(value => <option key={value} value={value}>{value}</option>)}
    </select>
  </label>;
  return <section className="panel filters">
    <div className="section-heading"><div><p className="eyebrow">01 · FILTERS</p><h2>Choose a journey view</h2></div><button className="button secondary" onClick={onReset}>Reset</button></div>
    <form onSubmit={onSubmit}>
      {field("station", "Station", options.stations, "All stations")}
      {field("journey_leg", "Journey leg", options.legs, "All journey legs")}
      {field("operator", "Operator", options.operators, "All operators")}
      {field("event_type", "Event", ["departure", "arrival"], "Arrivals & departures")}
      <label>From<input type="date" value={filters.from_date} onChange={event => onChange("from_date", event.target.value)} /></label>
      <label>To<input type="date" value={filters.to_date} onChange={event => onChange("to_date", event.target.value)} /></label>
      <button className="button primary" type="submit">Update view</button>
    </form>
  </section>;
}

function App() {
  const [filters, setFilters] = useState(initialFilters);
  const [options, setOptions] = useState({ stations: [], legs: [], operators: [] });
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true); setError("");
    try {
      const query = queryString(filters);
      const [reliability, delays, byHour, byDate, quality] = await Promise.all([
        getJson(`/api/v1/reliability?${query}`), getJson(`/api/v1/delays?${query}`),
        getJson(`/api/v1/reliability/by-hour?${query}`), getJson(`/api/v1/reliability/by-date?${query}`),
        getJson(`/api/v1/data-quality?${query}`),
      ]);
      setData({ reliability, delays, byHour, byDate, quality });
    } catch (requestError) { setError(requestError.message); } finally { setLoading(false); }
  };

  useEffect(() => {
    Promise.all([getJson("/api/v1/stations"), getJson("/api/v1/routes"), getJson("/api/v1/journey-legs")])
      .then(([stations, routes, legs]) => setOptions({
        stations: stations.stations.map(item => item.crs_code),
        operators: [...new Set(routes.routes.map(item => item.operator).filter(Boolean))],
        legs: legs.journey_legs,
      })).then(load).catch(requestError => { setError(requestError.message); setLoading(false); });
  }, []);

  const update = (name, value) => setFilters(current => ({ ...current, [name]: value }));
  const metrics = data?.reliability.metrics;
  return <main className="shell">
    <header className="masthead"><div><p className="eyebrow">TRACKRECORD · HISTORICAL VIEW</p><h1>Know the journey<br /><em>before you take it.</em></h1><p className="lede">Evidence-based reliability for the routes you use to get to university.</p></div><div className="source-badge">● National Rail HSP</div></header>
    <Filters filters={filters} options={options} onChange={update} onSubmit={event => { event.preventDefault(); load(); }} onReset={() => { setFilters(initialFilters); setTimeout(load, 0); }} />
    {error && <p className="panel error">{error}</p>}
    {loading && <p className="panel message">Loading reliability data…</p>}
    {!loading && !error && !metrics?.total_events && <p className="panel message">No records match these filters.</p>}
    {!loading && !error && metrics?.total_events > 0 && <Dashboard data={data} />}
    <footer>TrackRecord · Historical metrics, not live forecasts · Data coverage matters.</footer>
  </main>;
}

function Dashboard({ data }) {
  const { reliability, delays, byHour, byDate, quality } = data;
  const metrics = reliability.metrics;
  const denominator = Math.max(1, delays.total_observed_events);
  return <section>
    <div className="section-heading intro-heading"><div><p className="eyebrow">02 · OVERVIEW</p><h2>Your reliability snapshot</h2></div><p className="coverage-note">Coverage {formatPercent(metrics.coverage_percentage)} · {metrics.total_events} records</p></div>
    <div className="cards"><Card label="On-time services" value={formatPercent(metrics.on_time_percentage)} note={`${metrics.on_time_events} qualifying events`} /><Card label="Average delay" value={formatMinutes(metrics.average_delay_minutes)} note="observed, non-cancelled" /><Card label="Cancellation rate" value={formatPercent(metrics.cancellation_percentage)} note={`${metrics.cancelled_events} cancelled`} /><Card label="Records analysed" value={metrics.total_events} note={`${metrics.observed_events} with actual times`} /></div>
    <div className="grid">
      <section className="panel trend-panel"><div className="section-heading compact"><div><p className="eyebrow">03 · TREND</p><h2>Reliability by service date</h2></div></div><div className="trend-grid"><div><h3>On-time percentage</h3><BarList items={byDate.groups.map(group => ({ label: group.date, value: group.metrics.on_time_percentage }))} /></div><div><h3>Average delay</h3><BarList formatter={formatMinutes} items={byDate.groups.map(group => ({ label: group.date, value: group.metrics.average_delay_minutes }))} /></div></div><p className="caption">Each point represents the services in the selected operational date.</p></section>
      <section className="panel"><div className="section-heading compact"><div><p className="eyebrow">04 · DELAYS</p><h2>Delay distribution</h2></div></div><BarList items={[["On time", "early_or_on_time"], ["1–5 min", "1_to_5_minutes"], ["6–15 min", "6_to_15_minutes"], ["Over 15 min", "over_15_minutes"]].map(([label, key]) => ({ label, value: delays.bands[key] / denominator * 100 }))} /><p className="caption">Cancelled services are excluded from delay bands.</p></section>
      <section className="panel"><div className="section-heading compact"><div><p className="eyebrow">05 · BY HOUR</p><h2>Scheduled departure pattern</h2></div></div><BarList items={byHour.groups.map(group => ({ label: `${String(group.hour).padStart(2, "0")}:00`, value: group.metrics.on_time_percentage }))} /><p className="caption">On-time percentage by scheduled local hour.</p></section>
    </div>
    <section className="panel context"><div className="section-heading compact"><div><p className="eyebrow">06 · CONTEXT</p><h2>Data context</h2></div></div><dl className="context-grid"><div><dt>Source</dt><dd>{reliability.metadata.data_source}</dd></div><div><dt>Data period</dt><dd>{formatPeriod(reliability.metadata.data_period)}</dd></div><div><dt>Collection</dt><dd>{reliability.metadata.latest_collection ? `${reliability.metadata.latest_collection.status} · ${reliability.metadata.latest_collection.records_saved} saved` : "—"}</dd></div><div><dt>Missing actuals</dt><dd>{quality.quality.missing_actual_times}</dd></div><div><dt>Coverage</dt><dd>{formatPercent(metrics.coverage_percentage)}</dd></div><div><dt>Metric rule</dt><dd>On time ≤ 1 minute late</dd></div></dl></section>
  </section>;
}

function Card({ label, value, note }) { return <article className="card"><span>{label}</span><strong>{value}</strong><small>{note}</small></article>; }

createRoot(document.getElementById("root")).render(<App />);
