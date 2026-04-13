# Device Reports

`device_reports/` is the tracked, shareable layer for hardware-specific investigations.

Each report bundle should stay small enough to review in Git while still being useful for future comparison, regression checks, and onboarding.

## What belongs here

- `manifest.json` with device name, report type, capture dates, and key findings
- a markdown summary (`README.md`) with the durable conclusions
- machine-readable report data such as telemetry JSON
- lightweight helper assets only when they materially improve review

## What stays local

- original capture files such as `.OSV`, `.LRF`, and other large binaries
- raw `ffprobe` / `exiftool` dumps
- exploratory scratch notes and intermediate parsing outputs
- generated HTML renders

Those local artifacts belong in ignored workspaces like `report_data/`.

## Recommended layout

```text
device_reports/
  <device-slug>/
    <report-slug>/
      README.md
      manifest.json
      telemetry_report.json
```

## Rendering local HTML

For OSV telemetry bundles, build a local dashboard with:

```bash
python tools/build_osv_telemetry_report.py --report-dir device_reports/osmo-360/osv-telemetry-2026-04-12
```

That writes an ignored `report.html` next to the tracked files.
