const form = document.querySelector("#filter-form");
const loading = document.querySelector("#loading");
const empty = document.querySelector("#empty");
const content = document.querySelector("#content");
const errorBox = document.querySelector("#filter-error");

function queryString() {
  const params = new URLSearchParams();
  for (const [key, value] of new FormData(form)) if (value) params.set(key, value);
  return params.toString();
}

function formatPercent(value) {
  return value == null ? "—" : `${Number(value).toFixed(1)}%`;
}

function formatMinutes(value) {
  return value == null ? "—" : `${Number(value).toFixed(1)} min`;
}

function formatPeriod(period) {
  if (!period || !period.from || !period.to) return "—";
  return period.from === period.to ? period.from : `${period.from} → ${period.to}`;
}

function drawBars(container, entries, valueKey = "value", formatter = formatPercent) {
  container.replaceChildren();
  if (!entries.length) {
    container.textContent = "No grouped observations available.";
    return;
  }
  for (const entry of entries) {
    const row = document.createElement("div");
    row.className = "bar-row";
    const label = document.createElement("span");
    label.textContent = entry.label;
    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${Math.max(0, Math.min(100, entry[valueKey] ?? 0))}%`;
    track.append(fill);
    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = formatter(entry[valueKey]);
    row.append(label, track, value);
    container.append(row);
  }
}

function setSelectOptions(select, values, placeholder) {
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
  select.options[0].textContent = placeholder;
}

async function loadOptions() {
  const [stations, routes, journeyLegs] = await Promise.all([
    fetch("/api/v1/stations").then(readResponse),
    fetch("/api/v1/routes").then(readResponse),
    fetch("/api/v1/journey-legs").then(readResponse),
  ]);
  const stationItems = Array.isArray(stations.stations) ? stations.stations : [];
  const routeItems = Array.isArray(routes.routes) ? routes.routes : [];
  const legs = Array.isArray(journeyLegs.journey_legs) ? journeyLegs.journey_legs : [];
  setSelectOptions(document.querySelector("#station"), stationItems.map(item => item.crs_code), "All stations");
  setSelectOptions(document.querySelector("#journey_leg"), legs, "All journey legs");
  setSelectOptions(document.querySelector("#operator"), [...new Set(routeItems.map(item => item.operator).filter(Boolean))], "All operators");
}

async function loadDashboard() {
  loading.hidden = false;
  empty.hidden = true;
  content.hidden = true;
  errorBox.hidden = true;
  try {
    const query = queryString();
    const [reliability, delays, byHour, byDate] = await Promise.all([
      fetch(`/api/v1/reliability?${query}`).then(readResponse),
      fetch(`/api/v1/delays?${query}`).then(readResponse),
      fetch(`/api/v1/reliability/by-hour?${query}`).then(readResponse),
      fetch(`/api/v1/reliability/by-date?${query}`).then(readResponse),
    ]);
    const metrics = reliability.metrics;
    if (!metrics.total_events) {
      empty.hidden = false;
      return;
    }
    document.querySelector("#on-time").textContent = formatPercent(metrics.on_time_percentage);
    document.querySelector("#on-time-count").textContent = `${metrics.on_time_events} qualifying events`;
    document.querySelector("#average-delay").textContent = formatMinutes(metrics.average_delay_minutes);
    document.querySelector("#cancellation-rate").textContent = formatPercent(metrics.cancellation_percentage);
    document.querySelector("#cancelled-count").textContent = `${metrics.cancelled_events} cancelled`;
    document.querySelector("#sample-size").textContent = metrics.total_events;
    document.querySelector("#observed-count").textContent = `${metrics.observed_events} with actual times`;
    document.querySelector("#coverage").textContent = formatPercent(metrics.coverage_percentage);
    document.querySelector("#coverage-note").textContent = `Coverage ${formatPercent(metrics.coverage_percentage)} · ${metrics.total_events} records`;
    document.querySelector("#data-source").textContent = reliability.metadata.data_source;
    document.querySelector("#data-period").textContent = formatPeriod(reliability.metadata.data_period);
    document.querySelector("#last-observed").textContent = reliability.metadata.last_observed_at || "—";
    const collection = reliability.metadata.latest_collection;
    document.querySelector("#collection-status").textContent = collection
      ? `${collection.status} · ${collection.records_saved} saved`
      : "—";
    drawBars(document.querySelector("#delay-bars"), [
      { label: "On time", value: delays.bands.early_or_on_time / Math.max(1, delays.total_observed_events) * 100 },
      { label: "1–5 min", value: delays.bands["1_to_5_minutes"] / Math.max(1, delays.total_observed_events) * 100 },
      { label: "6–15 min", value: delays.bands["6_to_15_minutes"] / Math.max(1, delays.total_observed_events) * 100 },
      { label: "Over 15 min", value: delays.bands.over_15_minutes / Math.max(1, delays.total_observed_events) * 100 },
    ]);
    drawBars(document.querySelector("#hour-groups"), byHour.groups.map(group => ({
      label: `${String(group.hour).padStart(2, "0")}:00`,
      value: group.metrics.on_time_percentage,
    })));
    drawBars(document.querySelector("#date-reliability"), byDate.groups.map(group => ({
      label: group.date,
      value: group.metrics.on_time_percentage,
    })));
    drawBars(document.querySelector("#date-delay"), byDate.groups.map(group => ({
      label: group.date,
      value: group.metrics.average_delay_minutes,
    })), "value", formatMinutes);
    content.hidden = false;
  } catch (error) {
    errorBox.textContent = error.message || "Unable to load dashboard data.";
    errorBox.hidden = false;
  } finally {
    loading.hidden = true;
  }
}

async function readResponse(response) {
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "API request failed.");
  return body;
}

form.addEventListener("submit", event => { event.preventDefault(); loadDashboard(); });
document.querySelector("#reset-filters").addEventListener("click", () => { form.reset(); loadDashboard(); });
loadOptions().then(loadDashboard).catch(error => {
  loading.hidden = true;
  errorBox.textContent = error.message || "Unable to load filter options.";
  errorBox.hidden = false;
});
