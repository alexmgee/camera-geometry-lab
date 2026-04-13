# DJI Osmo 360 OSV Telemetry Report

This folder is the tracked, shareable slice of the first Osmo telemetry investigation.

## Included

- `manifest.json` for report metadata and review notes
- `telemetry_report.json` with the full tracked per-frame telemetry series

## Not Included

- the original `.OSV` / `.LRF` capture files
- raw `ffprobe` and `exiftool` dumps
- exploratory scratch outputs from `report_data/`
- generated `report.html`

## Why this bundle exists

The goal is to keep enough evidence in Git to compare devices and capture modes over time without bloating the repository with raw media or throwaway intermediate files.

## Headline findings

- ExifTool is sufficient for quaternion extraction on the Osmo 360.
- The tracked telemetry trace includes all 4003 video frames and passes basic quality checks.
- The LRF sidecar is useful for quick stitched-preview validation work.

## Rebuild the local HTML dashboard

```bash
python tools/build_osv_telemetry_report.py --report-dir device_reports/osmo-360/osv-telemetry-2026-04-12
```

That produces an ignored `report.html` beside this README for local review.
