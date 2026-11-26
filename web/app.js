"use strict";

const AGENT_URL = "http://127.0.0.1:8765/api/metrics";
const POLL_MS = 2000;
const HISTORY_POINTS = 150; // 5 minutes at 2 s
const SPEED_URL = "https://speed.cloudflare.com";

const $ = (id) => document.getElementById(id);

// ---------- formatting ----------
function fmtBytes(n) {
  if (n == null) return "–";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n >= 100 || i === 0 ? 0 : 1)} ${units[i]}`;
}
const fmtRate = (n) => (n == null ? "–" : `${fmtBytes(n)}/s`);
const fmtPct = (n) => (n == null ? "–" : `${n.toFixed(1)}%`);
function fmtDuration(sec) {
  const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60);
  return d ? `${d} วัน ${h} ชม. ${m} นาที` : `${h} ชม. ${m} นาที`;
}
const timeLabel = (ts) => new Date(ts * 1000).toLocaleTimeString("th-TH", { hour12: false });

// ---------- charts ----------
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const charts = [];

function makeChart(canvasId, series, { percent = false } = {}) {
  const chart = new Chart($(canvasId), {
    type: "line",
    data: { labels: [], datasets: series.map((s) => ({ label: s.label, data: [], borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, tension: 0.25, _color: s.color })) },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { ticks: { maxTicksLimit: 6, maxRotation: 0 }, grid: { display: false } },
        y: {
          beginAtZero: true,
          max: percent ? 100 : undefined,
          suggestedMax: percent ? undefined : 1024, // empty rate chart: 0–1 KB/s instead of repeated "1 B/s"
          ticks: { maxTicksLimit: 5, callback: (v) => (percent ? `${v}%` : fmtRate(v)) },
        },
      },
      plugins: {
        legend: { display: series.length > 1, position: "top", align: "end", labels: { boxWidth: 12, boxHeight: 2 } },
        tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${percent ? fmtPct(c.parsed.y) : fmtRate(c.parsed.y)}` } },
      },
    },
  });
  charts.push(chart);
  return chart;
}

function applyTheme() {
  const text2 = css("--text-secondary"), grid = css("--grid"), axis = css("--axis");
  Chart.defaults.color = text2;
  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", sans-serif';
  for (const chart of charts) {
    for (const ds of chart.data.datasets) {
      ds.borderColor = ds.backgroundColor = css(ds._color);
    }
    chart.options.scales.y.grid.color = grid;
    chart.options.scales.y.border = { color: axis };
    chart.options.scales.x.border = { color: axis };
    chart.update("none");
  }
}

const cpuChart = makeChart("c-cpu", [{ label: "CPU", color: "--series-1" }], { percent: true });
const memChart = makeChart("c-mem", [{ label: "Memory", color: "--series-1" }], { percent: true });
const netChart = makeChart("c-net", [{ label: "Download", color: "--series-1" }, { label: "Upload", color: "--series-2" }]);
const diskChart = makeChart("c-disk", [{ label: "Read", color: "--series-1" }, { label: "Write", color: "--series-2" }]);
applyTheme();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);

function pushPoint(chart, label, values) {
  chart.data.labels.push(label);
  chart.data.datasets.forEach((ds, i) => ds.data.push(values[i]));
  if (chart.data.labels.length > HISTORY_POINTS) {
    chart.data.labels.shift();
    chart.data.datasets.forEach((ds) => ds.data.shift());
  }
  chart.update("none");
}

// ---------- DOM helpers (textContent only: process names are untrusted) ----------
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v; else if (k === "style") node.style.cssText = v; else node.setAttribute(k, v);
  }
  for (const c of children) node.append(c);
  return node;
}
const bar = (pct, crit = false) => el("div", { class: crit ? "bar crit" : "bar" }, el("span", { style: `width:${Math.min(pct, 100)}%` }));

function renderKV(dl, pairs) {
  dl.replaceChildren(...pairs.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
}

// ---------- render ----------
function render(m) {
  const label = timeLabel(m.timestamp);

  $("t-cpu").textContent = fmtPct(m.cpu.percent);
  $("t-cpu-sub").textContent = m.cpu.freq_mhz ? `${(m.cpu.freq_mhz / 1000).toFixed(2)} GHz` : "";
  $("t-mem").textContent = fmtPct(m.memory.percent);
  $("t-mem-sub").textContent = `${fmtBytes(m.memory.used)} / ${fmtBytes(m.memory.total)}`;
  $("t-down").textContent = fmtRate(m.network?.bytes_recv_per_sec);
  $("t-up").textContent = fmtRate(m.network?.bytes_sent_per_sec);
  if (m.battery) {
    $("t-bat").textContent = `${Math.round(m.battery.percent)}%`;
    $("t-bat-sub").textContent = m.battery.plugged ? "🔌 กำลังชาร์จ / เสียบสาย" :
      m.battery.secs_left ? `ใช้ได้อีก ~${fmtDuration(m.battery.secs_left)}` : "ใช้แบตเตอรี่";
  } else {
    $("t-bat").textContent = "–";
    $("t-bat-sub").textContent = "ไม่พบแบตเตอรี่";
  }

  pushPoint(cpuChart, label, [m.cpu.percent]);
  pushPoint(memChart, label, [m.memory.percent]);
  pushPoint(netChart, label, [m.network?.bytes_recv_per_sec ?? null, m.network?.bytes_sent_per_sec ?? null]);
  pushPoint(diskChart, label, [m.disk_io?.read_bytes_per_sec ?? null, m.disk_io?.write_bytes_per_sec ?? null]);

  $("cores").replaceChildren(...m.cpu.per_core.map((p, i) =>
    el("div", { class: "core" }, el("span", { class: "muted" }, `#${i}`), bar(p), el("span", { class: "num" }, `${Math.round(p)}%`))));

  renderKV($("mem-detail"), [
    ["ใช้ไป", `${fmtBytes(m.memory.used)} จาก ${fmtBytes(m.memory.total)}`],
    ["Swap / Page file", `${fmtBytes(m.memory.swap_used)} จาก ${fmtBytes(m.memory.swap_total)} (${fmtPct(m.memory.swap_percent)})`],
  ]);

  $("disks").replaceChildren(...m.disks.map((d) => {
    if (d.error) return el("div", { class: "disk" }, el("div", { class: "disk-head" }, el("strong", {}, d.mount), el("span", { class: "muted" }, `อ่านไม่ได้: ${d.error}`)));
    const crit = d.percent >= 90;
    return el("div", { class: "disk" },
      el("div", { class: "disk-head" },
        el("strong", {}, `${d.mount} `, el("span", { class: "muted" }, d.fstype)),
        el("span", {}, crit ? el("span", { class: "warn-label" }, "⚠ เกือบเต็ม ") : "", `${fmtBytes(d.used)} / ${fmtBytes(d.total)} (${fmtPct(d.percent)}) · เหลือ ${fmtBytes(d.free)}`)),
      bar(d.percent, crit));
  }));

  renderKV($("sysinfo"), [
    ["OS", `${m.system.os} (${m.system.os_version})`],
    ["CPU", m.system.cpu_model || "–"],
    ["Cores", `${m.cpu.cores_physical} physical / ${m.cpu.cores_logical} logical`],
    ["Clock", m.cpu.freq_mhz ? `${(m.cpu.freq_mhz / 1000).toFixed(2)} GHz (max ${(m.cpu.freq_max_mhz / 1000).toFixed(2)} GHz)` : "–"],
    ["Uptime", fmtDuration(m.system.uptime_sec)],
    ["เปิดเครื่องเมื่อ", new Date(m.system.boot_time * 1000).toLocaleString("th-TH")],
  ]);

  const procRows = (list) => list.map((p) => el("tr", {},
    el("td", { title: p.name }, p.name), el("td", { class: "num" }, String(p.pid)),
    el("td", { class: "num" }, fmtPct(p.cpu_percent)), el("td", { class: "num" }, fmtBytes(p.memory_rss))));
  $("p-cpu").replaceChildren(...procRows(m.processes.by_cpu));
  $("p-mem").replaceChildren(...procRows(m.processes.by_memory));

  $("updated").textContent = `อัปเดตล่าสุด ${label}`;
}

function setConnected(ok, detail) {
  const pill = $("status");
  pill.className = `pill ${ok ? "pill-ok" : "pill-bad"}`;
  $("status-text").textContent = ok ? "เชื่อมต่อ agent แล้ว" : "ไม่พบ agent";
  pill.title = detail || "";
  $("offline").hidden = ok;
  for (const card of document.querySelectorAll("#dash > section:not(:last-child)")) card.classList.toggle("stale", !ok);
}

async function poll() {
  try {
    // targetAddressSpace: Chrome Local Network Access hint; ignored by other browsers.
    const res = await fetch(AGENT_URL, { cache: "no-store", targetAddressSpace: "loopback", signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`agent ตอบกลับ HTTP ${res.status}`);
    render(await res.json());
    setConnected(true);
  } catch (err) {
    console.warn("agent poll failed:", err);
    setConnected(false, String(err));
  } finally {
    setTimeout(poll, POLL_MS);
  }
}
poll();

// ---------- speedtest (Cloudflare) ----------
const median = (a) => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
const mbps = (bytes, sec) => (bytes * 8) / sec / 1e6;

async function timed(fn) {
  const t0 = performance.now();
  await fn();
  return (performance.now() - t0) / 1000;
}

async function measurePing() {
  const samples = [];
  for (let i = 0; i < 8; i++) {
    samples.push(await timed(async () => {
      const r = await fetch(`${SPEED_URL}/__down?bytes=0&r=${Math.random()}`, { cache: "no-store" });
      await r.arrayBuffer();
    }));
  }
  return median(samples) * 1000;
}

// Grow the transfer size until one transfer takes long enough to be meaningful.
async function measureThroughput(transfer, maxBytes) {
  let bytes = 100_000, result = 0;
  while (true) {
    const sec = await timed(() => transfer(bytes));
    result = mbps(bytes, sec);
    if (sec >= 1.5 || bytes >= maxBytes) return result;
    bytes = Math.min(bytes * (sec < 0.3 ? 10 : 4), maxBytes);
  }
}

async function download(bytes) {
  const r = await fetch(`${SPEED_URL}/__down?bytes=${bytes}&r=${Math.random()}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`download HTTP ${r.status}`);
  await r.arrayBuffer();
}

async function upload(bytes) {
  const r = await fetch(`${SPEED_URL}/__up?r=${Math.random()}`, { method: "POST", body: new Uint8Array(bytes), cache: "no-store" });
  if (!r.ok) throw new Error(`upload HTTP ${r.status}`);
  await r.arrayBuffer();
}

$("st-btn").addEventListener("click", async () => {
  const btn = $("st-btn"), state = $("st-state");
  btn.disabled = true;
  for (const id of ["st-ping", "st-down", "st-up"]) $(id).textContent = "–";
  try {
    state.textContent = "กำลังวัด ping…";
    $("st-ping").textContent = `${(await measurePing()).toFixed(0)} ms`;
    state.textContent = "กำลังวัด download…";
    $("st-down").textContent = `${(await measureThroughput(download, 100_000_000)).toFixed(1)} Mbps`;
    state.textContent = "กำลังวัด upload…";
    $("st-up").textContent = `${(await measureThroughput(upload, 25_000_000)).toFixed(1)} Mbps`;
    state.textContent = `เสร็จแล้ว (${new Date().toLocaleTimeString("th-TH", { hour12: false })})`;
  } catch (err) {
    console.error("speedtest failed:", err);
    state.textContent = `ทดสอบไม่สำเร็จ: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
});
