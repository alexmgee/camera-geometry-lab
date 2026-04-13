"""Build a shareable HTML dashboard for a curated OSV telemetry report bundle."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


DEFAULT_COMMANDS: dict[str, list[dict[str, str]]] = {
    "osv_telemetry": [
        {
            "title": "Probe container structure",
            "command": "ffprobe -v quiet -print_format json -show_format -show_streams file.osv",
        },
        {
            "title": "Dump embedded telemetry",
            "command": "exiftool -ee -a -u -n file.osv",
        },
        {
            "title": "Extract a preview frame from the LRF sidecar",
            "command": "ffmpeg -i file.LRF -vframes 1 -map 0:0 preview_erp.png",
        },
    ]
}


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__HTML_TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#fcfcfa;
  --paper:#ffffff;
  --ink:#171717;
  --muted:#676767;
  --border:#d9d7d2;
  --soft:#f4f2ed;
  --accent:#24414d;
  --accent-soft:#dbe6ea;
  --ok:#1e6a44;
  --warn:#926100;
}
body{
  font-family:Georgia,"Times New Roman",serif;
  background:linear-gradient(180deg,#f7f5f0 0%,#fcfcfa 220px);
  color:var(--ink);
  line-height:1.7;
  font-size:15px;
}
.shell{
  max-width:1160px;
  margin:0 auto;
  padding:32px 24px 56px;
}
.hero{
  background:var(--paper);
  border:1px solid var(--border);
  padding:28px;
  box-shadow:0 10px 30px rgba(0,0,0,0.04);
}
.eyebrow{
  font:600 12px/1.2 "Helvetica Neue",Helvetica,Arial,sans-serif;
  letter-spacing:0.10em;
  text-transform:uppercase;
  color:var(--accent);
  margin-bottom:10px;
}
h1{
  font-size:32px;
  line-height:1.15;
  margin-bottom:8px;
}
.subtitle{
  color:var(--muted);
  max-width:760px;
}
.hero-grid{
  display:grid;
  grid-template-columns:2fr 1fr;
  gap:22px;
  margin-top:24px;
}
.panel{
  background:var(--paper);
  border:1px solid var(--border);
  padding:20px;
}
.panel h2{
  font:700 13px/1.2 "Helvetica Neue",Helvetica,Arial,sans-serif;
  letter-spacing:0.08em;
  text-transform:uppercase;
  color:var(--muted);
  margin-bottom:14px;
}
.source-table{
  width:100%;
  border-collapse:collapse;
  font:14px/1.5 "Helvetica Neue",Helvetica,Arial,sans-serif;
}
.source-table td{
  padding:8px 0;
  border-bottom:1px solid #ece9e2;
  vertical-align:top;
}
.source-table td:first-child{
  width:38%;
  color:var(--muted);
  padding-right:12px;
}
.bullets{
  padding-left:18px;
}
.bullets li{
  margin:0 0 8px;
}
.stats{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:16px;
  margin:24px 0 28px;
}
.stat{
  background:var(--paper);
  border:1px solid var(--border);
  padding:18px 18px 16px;
}
.stat .value{
  font:700 30px/1 "Helvetica Neue",Helvetica,Arial,sans-serif;
  color:var(--ink);
}
.stat .label{
  font:700 12px/1.2 "Helvetica Neue",Helvetica,Arial,sans-serif;
  letter-spacing:0.08em;
  text-transform:uppercase;
  color:var(--muted);
  margin-top:8px;
}
.stat .detail{
  color:var(--muted);
  font-size:13px;
  margin-top:6px;
}
.section{
  margin-top:28px;
}
.section-card{
  background:var(--paper);
  border:1px solid var(--border);
  padding:24px;
}
.section-card + .section-card{
  margin-top:16px;
}
.section-title{
  font-size:24px;
  line-height:1.15;
  margin-bottom:10px;
}
.section-intro{
  color:var(--muted);
  max-width:860px;
  margin-bottom:18px;
}
.grid-2{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(320px,1fr));
  gap:16px;
}
.card{
  background:var(--soft);
  border:1px solid #e7e1d6;
  padding:18px;
}
.card h3{
  font:700 13px/1.2 "Helvetica Neue",Helvetica,Arial,sans-serif;
  letter-spacing:0.06em;
  text-transform:uppercase;
  color:var(--muted);
  margin-bottom:10px;
}
.chart-box{
  background:var(--soft);
  border:1px solid #e7e1d6;
  padding:18px;
}
.chart-box h3{
  font:700 13px/1.2 "Helvetica Neue",Helvetica,Arial,sans-serif;
  letter-spacing:0.06em;
  text-transform:uppercase;
  color:var(--muted);
  margin-bottom:12px;
}
.chart-wrap{
  position:relative;
  height:320px;
}
.code{
  background:#f2eee6;
  border:1px solid #e1d7c7;
  padding:14px;
  overflow:auto;
  font:13px/1.6 Consolas,"SFMono-Regular","Liberation Mono",monospace;
}
.code + .code{
  margin-top:12px;
}
.quality-table{
  width:100%;
  border-collapse:collapse;
  font:14px/1.5 "Helvetica Neue",Helvetica,Arial,sans-serif;
}
.quality-table th,
.quality-table td{
  padding:10px 12px;
  border-bottom:1px solid #ece9e2;
  text-align:left;
}
.quality-table th{
  color:var(--muted);
  font-size:12px;
  letter-spacing:0.08em;
  text-transform:uppercase;
}
.badge{
  display:inline-block;
  padding:3px 8px;
  border-radius:999px;
  font:700 11px/1.2 "Helvetica Neue",Helvetica,Arial,sans-serif;
  letter-spacing:0.06em;
  text-transform:uppercase;
}
.badge-ok{
  background:#dff1e7;
  color:var(--ok);
}
.badge-warn{
  background:#f9ecd1;
  color:var(--warn);
}
.foot{
  color:var(--muted);
  margin-top:18px;
  font-size:13px;
}
@media (max-width: 860px){
  .hero-grid{grid-template-columns:1fr}
  h1{font-size:28px}
}
</style>
</head>
<body>
<div class="shell">
  <section class="hero">
    <div class="eyebrow">Device Report</div>
    <h1>__REPORT_TITLE__</h1>
    <p class="subtitle">__REPORT_SUBTITLE__</p>
    <div class="hero-grid">
      <div class="panel">
        <h2>Key Findings</h2>
        __KEY_FINDINGS_HTML__
      </div>
      <div class="panel">
        <h2>Report Bundle</h2>
        <table class="source-table">__SOURCE_ROWS_HTML__</table>
      </div>
    </div>
  </section>

  <section class="stats">
    <div class="stat"><div class="value">__STAT_FRAMES__</div><div class="label">Quaternion Frames</div><div class="detail">Tracked full telemetry series stored in JSON</div></div>
    <div class="stat"><div class="value">__STAT_NORM__</div><div class="label">Mean Norm</div><div class="detail">Valid rotation quaternions stay near 1.0</div></div>
    <div class="stat"><div class="value">__STAT_DELTA__</div><div class="label">Max Delta</div><div class="detail">Largest frame-to-frame orientation jump</div></div>
    <div class="stat"><div class="value">__STAT_ACCEL__</div><div class="label">Mean |a|</div><div class="detail">Average accelerometer magnitude in g</div></div>
  </section>

  <section class="section">
    <div class="section-card">
      <h2 class="section-title">Context</h2>
      <p class="section-intro">This rendered dashboard is built from a curated report bundle committed to the repository. The large raw capture files, raw telemetry dumps, and generated scratch outputs stay local, while the shareable findings and tracked telemetry traces remain reviewable in Git.</p>
      <div class="grid-2">
        <div class="card">
          <h3>Report Notes</h3>
          __REPORT_NOTES_HTML__
        </div>
        <div class="card">
          <h3>Related Docs</h3>
          __RELATED_DOCS_HTML__
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="section-card">
      <h2 class="section-title">Quaternion Signals</h2>
      <p class="section-intro">The top plot shows the quaternion components over time. Smooth curves and a flat unit-norm line are the two quick sanity checks that matter most for downstream reprojection and gravity compensation work.</p>
      <div class="chart-box">
        <h3>Quaternion Components</h3>
        <div class="chart-wrap"><canvas id="quatChart"></canvas></div>
      </div>
      <div class="chart-box" style="margin-top:16px">
        <h3>Quaternion Norm</h3>
        <div class="chart-wrap"><canvas id="normChart"></canvas></div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="section-card">
      <h2 class="section-title">Euler View</h2>
      <p class="section-intro">Euler angles are easier to read than quaternions for quick inspection, even though they are only a visualization layer. Large spans here indicate broad camera motion coverage during the capture.</p>
      <div class="chart-box">
        <h3>Yaw / Pitch / Roll</h3>
        <div class="chart-wrap"><canvas id="eulerChart"></canvas></div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="section-card">
      <h2 class="section-title">Accelerometer</h2>
      <p class="section-intro">The accelerometer traces help confirm that the IMU is active and behaving plausibly. Magnitude hovering near 1 g is expected, with higher spikes during motion.</p>
      <div class="grid-2">
        <div class="chart-box">
          <h3>Component Traces</h3>
          <div class="chart-wrap"><canvas id="accelChart"></canvas></div>
        </div>
        <div class="chart-box">
          <h3>Magnitude</h3>
          <div class="chart-wrap"><canvas id="accelMagChart"></canvas></div>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="section-card">
      <h2 class="section-title">Validation</h2>
      <p class="section-intro">These checks are simple repo-friendly quality gates. They turn the report bundle into something we can review and compare over time as more devices and capture modes are added.</p>
      <div class="grid-2">
        <div class="card">
          <h3>Quality Checks</h3>
          <table class="quality-table">
            <thead>
              <tr><th>Check</th><th>Measured</th><th>Result</th></tr>
            </thead>
            <tbody id="qualityTable"></tbody>
          </table>
        </div>
        <div class="chart-box">
          <h3>Frame-to-Frame Delta</h3>
          <div class="chart-wrap"><canvas id="deltaChart"></canvas></div>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="section-card">
      <h2 class="section-title">Reproduce</h2>
      <p class="section-intro">These commands are the lightweight reproduction path for this report type. The committed report bundle is intentionally smaller than the original scratch workspace.</p>
      __COMMAND_CARDS_HTML__
      <p class="foot">Rendered from <code>__MANIFEST_NAME__</code> and <code>__DATA_FILE_NAME__</code>.</p>
    </div>
  </section>
</div>

<script>
const DATA = __DATA_JSON__;
const S = DATA.stats;

const tests = [
  ['Quaternion frames', String(S.quat_frames), S.quat_frames === S.total_frames],
  ['Unit norm minimum > 0.999', S.norm_min.toFixed(10), S.norm_min > 0.999],
  ['Unit norm maximum < 1.001', S.norm_max.toFixed(10), S.norm_max < 1.001],
  ['Max frame delta < 0.1', S.delta_max.toFixed(6), S.delta_max < 0.1],
  ['Zero quaternion count = 0', String(S.zero_quat_count), S.zero_quat_count === 0],
  ['Mean accel magnitude between 0.8 and 1.2 g', S.accel_mag_mean.toFixed(4) + ' g', S.accel_mag_mean > 0.8 && S.accel_mag_mean < 1.2],
];

const qualityTable = document.getElementById('qualityTable');
tests.forEach(([label, measured, pass]) => {
  const row = document.createElement('tr');
  row.innerHTML = '<td>' + label + '</td><td><strong>' + measured + '</strong></td><td><span class="badge ' + (pass ? 'badge-ok">Pass' : 'badge-warn">Review') + '</span></td>';
  qualityTable.appendChild(row);
});

const colors = {
  ink: '#171717',
  red: '#b03a2e',
  green: '#2e7d4f',
  blue: '#2a5f86',
  gold: '#8b6a1f',
  violet: '#6d4f8c',
};

const baseOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  elements: { point: { radius: 0 }, line: { borderWidth: 1.5 } },
  plugins: {
    legend: {
      labels: {
        color: '#555',
        font: { family: '"Helvetica Neue",Helvetica,Arial,sans-serif', size: 11 },
      },
    },
  },
  scales: {
    x: {
      ticks: { color: '#777', maxTicksLimit: 10 },
      grid: { color: '#e9e6df' },
      title: { display: true, text: 'Time (s)', color: '#777' },
    },
    y: {
      ticks: { color: '#777' },
      grid: { color: '#e9e6df' },
    },
  },
};

new Chart('quatChart', {
  type: 'line',
  data: {
    labels: DATA.quaternions.map((d) => d.t),
    datasets: [
      { label: 'w', data: DATA.quaternions.map((d) => d.qw), borderColor: colors.ink },
      { label: 'x', data: DATA.quaternions.map((d) => d.qx), borderColor: colors.red },
      { label: 'y', data: DATA.quaternions.map((d) => d.qy), borderColor: colors.green },
      { label: 'z', data: DATA.quaternions.map((d) => d.qz), borderColor: colors.blue },
    ],
  },
  options: baseOptions,
});

new Chart('normChart', {
  type: 'line',
  data: {
    labels: DATA.quaternions.map((d) => d.t),
    datasets: [{ label: 'norm', data: DATA.quaternions.map((d) => d.norm), borderColor: colors.ink }],
  },
  options: {
    ...baseOptions,
    scales: {
      ...baseOptions.scales,
      y: { ...baseOptions.scales.y, min: 0.9999998, max: 1.0000002 },
    },
  },
});

new Chart('eulerChart', {
  type: 'line',
  data: {
    labels: DATA.euler.map((d) => d.t),
    datasets: [
      { label: 'yaw', data: DATA.euler.map((d) => d.yaw), borderColor: colors.blue },
      { label: 'pitch', data: DATA.euler.map((d) => d.pitch), borderColor: colors.green },
      { label: 'roll', data: DATA.euler.map((d) => d.roll), borderColor: colors.red },
    ],
  },
  options: baseOptions,
});

new Chart('accelChart', {
  type: 'line',
  data: {
    labels: DATA.accelerometer.map((d) => d.t),
    datasets: [
      { label: 'ax', data: DATA.accelerometer.map((d) => d.ax), borderColor: colors.red },
      { label: 'ay', data: DATA.accelerometer.map((d) => d.ay), borderColor: colors.green },
      { label: 'az', data: DATA.accelerometer.map((d) => d.az), borderColor: colors.blue },
    ],
  },
  options: baseOptions,
});

new Chart('accelMagChart', {
  type: 'line',
  data: {
    labels: DATA.accelerometer.map((d) => d.t),
    datasets: [{ label: '|a|', data: DATA.accelerometer.map((d) => d.amag), borderColor: colors.violet }],
  },
  options: baseOptions,
});

new Chart('deltaChart', {
  type: 'line',
  data: {
    labels: DATA.deltas.map((d) => d.t),
    datasets: [{
      label: 'delta',
      data: DATA.deltas.map((d) => d.delta),
      borderColor: colors.gold,
      fill: { target: 'origin', above: 'rgba(139,106,31,0.12)' },
    }],
  },
  options: baseOptions,
});
</script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a curated OSV telemetry report bundle into a local HTML dashboard."
    )
    parser.add_argument(
        "--report-dir",
        required=True,
        type=Path,
        help="Directory containing manifest.json and the curated report JSON data.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional HTML output path. Defaults to <report-dir>/report.html.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_data(data: dict[str, Any]) -> None:
    required_top_level = {"stats", "quaternions", "euler", "accelerometer", "deltas"}
    missing = sorted(required_top_level - set(data))
    if missing:
        raise ValueError(f"Missing telemetry report keys: {', '.join(missing)}")

    required_stats = {
        "total_frames",
        "quat_frames",
        "norm_mean",
        "delta_max",
        "accel_mag_mean",
        "zero_quat_count",
        "norm_min",
        "norm_max",
    }
    stats = data["stats"]
    missing_stats = sorted(required_stats - set(stats))
    if missing_stats:
        raise ValueError(f"Missing telemetry stats: {', '.join(missing_stats)}")


def build_source_rows(manifest: dict[str, Any], data_file: Path) -> str:
    rows: list[tuple[str, str]] = [
        ("Device", str(manifest["device_name"])),
        ("Report Type", str(manifest["report_type"])),
        ("Bundle Path", str(manifest["report_slug"])),
        ("Data File", data_file.name),
    ]

    primary_asset = manifest.get("primary_asset")
    if primary_asset:
        rows.append(("Primary Asset", str(primary_asset)))

    sidecar_asset = manifest.get("sidecar_asset")
    if sidecar_asset:
        rows.append(("Sidecar Asset", str(sidecar_asset)))

    captured_date = manifest.get("captured_date")
    if captured_date:
        rows.append(("Captured", str(captured_date)))

    analysis_date = manifest.get("analysis_date")
    if analysis_date:
        rows.append(("Analyzed", str(analysis_date)))

    serial = manifest.get("serial")
    if serial:
        rows.append(("Serial", str(serial)))
    elif manifest.get("serial_redacted"):
        rows.append(("Serial", "Redacted"))

    return "".join(
        f"<tr><td>{html.escape(label)}</td><td><strong>{html.escape(value)}</strong></td></tr>"
        for label, value in rows
    )


def build_bullets(items: list[str], empty_message: str) -> str:
    if not items:
        return f"<p>{html.escape(empty_message)}</p>"
    rendered = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f"<ul class=\"bullets\">{rendered}</ul>"


def build_related_docs(items: list[str]) -> str:
    if not items:
        return "<p>No related docs listed.</p>"
    rendered = "".join(f"<li><code>{html.escape(item)}</code></li>" for item in items)
    return f"<ul class=\"bullets\">{rendered}</ul>"


def build_command_cards(commands: list[dict[str, str]]) -> str:
    if not commands:
        return "<p>No reproduction commands listed.</p>"

    cards: list[str] = []
    for command in commands:
        cards.append(
            "<div class=\"code\"><strong>"
            + html.escape(command["title"])
            + "</strong><br><br>"
            + html.escape(command["command"])
            + "</div>"
        )
    return "".join(cards)


def stat_text(value: float, digits: int = 3, suffix: str = "") -> str:
    return f"{value:.{digits}f}{suffix}"


def render_html(manifest: dict[str, Any], data: dict[str, Any], data_file: Path) -> str:
    stats = data["stats"]
    commands = manifest.get("commands") or DEFAULT_COMMANDS.get(manifest["report_type"], [])

    replacements = {
        "__HTML_TITLE__": html.escape(manifest["report_title"]),
        "__REPORT_TITLE__": html.escape(manifest["report_title"]),
        "__REPORT_SUBTITLE__": html.escape(manifest["subtitle"]),
        "__KEY_FINDINGS_HTML__": build_bullets(
            manifest.get("key_findings", []),
            "No key findings listed yet.",
        ),
        "__SOURCE_ROWS_HTML__": build_source_rows(manifest, data_file),
        "__STAT_FRAMES__": str(stats["quat_frames"]),
        "__STAT_NORM__": stat_text(stats["norm_mean"]),
        "__STAT_DELTA__": stat_text(stats["delta_max"]),
        "__STAT_ACCEL__": stat_text(stats["accel_mag_mean"], suffix=" g"),
        "__REPORT_NOTES_HTML__": build_bullets(
            manifest.get("report_notes", []),
            "No report notes listed yet.",
        ),
        "__RELATED_DOCS_HTML__": build_related_docs(manifest.get("related_docs", [])),
        "__COMMAND_CARDS_HTML__": build_command_cards(commands),
        "__MANIFEST_NAME__": html.escape(manifest.get("manifest_name", "manifest.json")),
        "__DATA_FILE_NAME__": html.escape(data_file.name),
        "__DATA_JSON__": json.dumps(data, separators=(",", ":")),
    }

    rendered = HTML_TEMPLATE
    for needle, replacement in replacements.items():
        rendered = rendered.replace(needle, replacement)
    return rendered


def load_report_bundle(report_dir: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    manifest_path = report_dir / "manifest.json"
    manifest = read_json(manifest_path)
    manifest.setdefault("manifest_name", manifest_path.name)
    manifest.setdefault("report_slug", report_dir.as_posix())

    data_file = report_dir / manifest.get("data_file", "telemetry_report.json")
    data = read_json(data_file)
    validate_data(data)
    return manifest, data, data_file


def main() -> int:
    args = parse_args()
    report_dir = args.report_dir.resolve()
    manifest, data, data_file = load_report_bundle(report_dir)
    output_path = args.output.resolve() if args.output else report_dir / "report.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(manifest, data, data_file), encoding="utf-8")
    print(f"Wrote report HTML: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
