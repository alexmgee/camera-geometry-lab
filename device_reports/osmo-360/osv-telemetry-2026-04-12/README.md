# DJI Osmo 360 OSV Telemetry Report

This folder is the tracked, shareable slice of the first Osmo telemetry investigation.

## Included

- `manifest.json` for report metadata and review notes
- `telemetry_report.json` with the full tracked per-frame telemetry series
- `osv_telemetry_report.html` interactive dashboard (self-contained, open in any browser)
- `OSV_Telemetry_Report.md` detailed written findings

## Source files (too large for git)

- [CAM_20260323172324_0023_D.OSV](TODO_GDRIVE_LINK) — 1.7 GB, dual-fisheye 3840x3840 HEVC, 50fps, 80s
- [CAM_20260323172324_0023_D.LRF](TODO_GDRIVE_LINK) — 88 MB, pre-stitched 2048x1024 equirectangular, 25fps

## Not included

- raw `ffprobe` and `exiftool` dumps
- exploratory scratch outputs from `report_data/`

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
