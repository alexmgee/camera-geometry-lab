# OSV Format Investigation

Living investigation document for DJI Osmo 360 `.osv` file analysis. Tracks what we know, what we don't, and what to try next.

**Camera:** DJI Osmo 360 (dual 1"-type sensors, 8K panoramic)
**Started:** 2026-04-12
**Last updated:** 2026-04-13

---

## Files analyzed so far

| File | Source | Duration | Frames | Notes |
|------|--------|----------|--------|-------|
| `CAM_20260323172324_0023_D.OSV` | `D:\Capture\deskTest\` | 80.06s @ 50fps | 4003 | First analysis. Alien-eye handheld capture. Full report in device bundle. |

Additional OSV files available for future analysis at `D:\Capture\` across captures: ashland (2), beachevening (3), beachTest (1), boueyThing (1), deskTest (1), outsideRink (6), plantTest (1), sunkenGardens2025 (4+).

---

## Established facts

### Container structure

OSV is an ISO Base Media File Format (MP4) container. The `deskTest` clip has 8 streams:

| Stream | Type | Codec tag | Content | Per-frame | Bitrate |
|--------|------|-----------|---------|-----------|---------|
| 0 | video | `hvc1` | Front lens, 3840x3840, HEVC Main 10, 10-bit | 4003 | 85.0 Mbps |
| 1 | video | `hvc1` | Back lens, 3840x3840, HEVC Main 10, 10-bit | 4003 | 85.0 Mbps |
| 2 | audio | `mp4a` | AAC 48kHz stereo | 3753 | 317 kbps |
| 3 | data | `djmd` | Primary telemetry ("CAM meta") | 4003 | 255 kbps |
| 4 | data | `djmd` | Secondary telemetry ("CAM meta") | 4003 | 57 kbps |
| 5 | data | `dbgi` | Debug info ("CAM dbgi") — front? | 4003 | 1.58 Mbps |
| 6 | data | `dbgi` | Debug info ("CAM dbgi") — back? | 4003 | 1.58 Mbps |
| 7 | video | MJPEG | Embedded thumbnail, 688x344 | 1 | — |

Additional MP4 boxes: `ftyp`, `free` (4044 bytes), `mdat` (1.74 GB), `moov`, `camd` (3.2 MB).

Format metadata: `encoder: Osmo 360`, `major_brand: isom`, `compatible_brands: isom, iso2, mp41`.

Source: ffprobe output in `report_data/osv_ffprobe.json`.

### LRF sidecar

The `.LRF` file (88 MB) that ships alongside every `.osv` is **not** just a thumbnail — it's a fully stitched low-res equirectangular:

| Stream | Type | Codec | Content | Per-frame |
|--------|------|-------|---------|-----------|
| 0 | video | H.264 High | 2048x1024 ERP, 8-bit, 25fps | 2002 |
| 1 | audio | AAC | 48kHz stereo | 3753 |
| 2 | data | `djmd` | Telemetry at 25fps | 2002 |
| 3 | data | `djmd` | Secondary telemetry at 25fps | 2002 |
| 4 | video | MJPEG | 688x344 thumbnail | 1 |

No `dbgi` tracks in LRF. Half framerate (25fps vs 50fps). The LRF ERP is gravity-corrected (horizon-leveled), just like DJI Studio output would be. This makes LRF the fast path for body-frame validation.

### Protobuf schema

The telemetry self-identifies via ExifTool's `Category` field:

```
pb_file:dvtm_oq101.proto; model_name:OQ001; pb_version:2.0.8; pb_lib_version:02.01.15;
```

ExifTool v13.41+ has built-in decoding support. No custom proto compilation or proprietary tools required.

Schema reference: https://exiftool.org/TagNames/DJI.html (lists `dvtm_oq101.proto` among 15+ DJI camera protos).

### Per-frame quaternions (proto path `3-2-9`)

Orientation quaternions are confirmed at 50 Hz, one per video frame, as 4x float32:

| Proto path | Component |
|-----------|-----------|
| `3-2-9-1` | w |
| `3-2-9-2` | x |
| `3-2-9-3` | y |
| `3-2-9-4` | z |

Quality from the `deskTest` clip:

| Metric | Value |
|--------|-------|
| Coverage | 4003/4003 frames |
| Norm min / max / mean | 0.9999999308 / 1.0000001358 / 1.0000000388 |
| Max frame-to-frame delta | 0.0436 (at t=56.26s) |
| Mean frame-to-frame delta | 0.003714 |
| Discontinuities (delta > 0.5) | 0 |
| Zero-quaternion frames | 0 |
| Component ranges | w: [0.130, 0.821], x: [-0.727, 0.316], y: [-0.784, 0.429], z: [-0.642, 0.744] |

Wide component ranges confirm the camera swept most of the orientation sphere during the 80s alien-eye capture.

DJI records **pre-computed sensor fusion output**, not raw gyro/accelerometer. The quaternion represents the camera's orientation in a gravity-aligned reference frame — this is the rotation the stitcher uses to level the horizon. Confirmed by Gyroflow docs: "DJI doesn't record the IMU data directly... it only contains Quaternions, which is the final computed camera position."

### Per-frame accelerometer (proto path `3-2-10`)

| Proto path | Component | Unit |
|-----------|-----------|------|
| `3-2-10-2` | X | g |
| `3-2-10-3` | Y | g |
| `3-2-10-4` | Z | g |

Magnitude mean: 1.0045g. Range: 0.74g to 2.32g. Consistent with handheld walking dynamics.

### Other confirmed per-frame fields

| Proto path | Field | Type | Notes |
|-----------|-------|------|-------|
| `3-2-3-1` | ISO | int | Auto-exposure |
| `3-2-4-1` | Shutter Speed | float32 | |
| `3-2-5-1` | Unknown | float32 | Always 1.0 in deskTest |
| `3-2-6-1` | Color Temperature | float32 | White balance |
| `3-2-15-1..7` | Exposure parameters | float32 | 7 values, includes EV / dynamic range |
| `3-2-16-1` | Unknown | float32 | Always 25.0 in deskTest |
| `3-2-17-1` | Unknown | rational | 100/1000 = 0.1 in deskTest |

### Device identification fields (proto message 1)

| Proto path | Field | Value (deskTest) |
|-----------|-------|------------------|
| `1-1-1` | Proto file | dvtm_oq101.proto |
| `1-1-3` | Proto version | 2.0.8 |
| `1-1-5` | Serial number | 95SXN7S02213TB |
| `1-1-6` | Firmware | 10.00.25.29 |
| `1-1-9` | Device ID | 8548286131 |
| `1-1-10` | Model | Osmo 360 |
| `1-11-1` | Framerate | 49.999 |
| `1-14-2` | Sensor dimension | 3840 |

### GPS (proto path `3-4`)

GPS fields exist in the schema but are **all zeroed** without the DJI remote control connected. The remote was not used for the deskTest capture. Fields: `3-4-2-1` (coordinates), `3-4-2-2` (altitude), `3-4-2-6-1` (date/time string).

### Simplest extraction command

```bash
exiftool -ee -a -u -n <file>.osv \
  | grep -E "^(Sample Time|Dvtm oq 101 3-2-9-[1234]|Accelerometer)"
```

---

## Open threads

### 1. Secondary `djmd` track (stream 4)

The primary `djmd` track (stream 3) runs at 255 kbps. Stream 4 is also tagged `djmd` / "CAM meta" but only 57 kbps — roughly 1/4 the data rate. Unknown whether it contains different fields, a subset, or data for the second lens.

**To investigate:** Run ExifTool with stream-specific extraction if possible, or extract stream 4 with ffmpeg and compare the protobuf structure to stream 3. Compare with the LRF's two `djmd` tracks (219 + 29 kbps — similar ratio).

### 2. High-rate quaternion sub-samples (proto path `3-3-2`)

Beyond the per-frame quaternion at `3-2-9`, there's a high-rate stream at `3-3-2-N-3`:

| Proto path | Content |
|-----------|---------|
| `3-3-2-N-1` | Raw timestamp |
| `3-3-2-N-2` | Sub-sample sequence index |
| `3-3-2-N-3-{1,2,3,4}` | Quaternion (w, x, y, z) |
| `3-3-2-N-4` | Unknown float |

79,616 sub-samples across 4003 frames = ~19.9 per frame = ~1000 Hz IMU fusion rate.

The `N` index alternates between sub-groups 1 and 2. Unknown whether these represent front/back lens sensor fusion, or two phases of the pipeline.

**To investigate:** Extract sub-group 1 vs sub-group 2 quaternions and compare. Do they diverge? Is one delayed relative to the other? Does interpolating at the video timestamp reproduce the per-frame quaternion at `3-2-9`?

### 3. Unknown likely-important fields

| Proto path | Observed value | Hypothesis | Confidence |
|-----------|---------------|------------|------------|
| `1-3-1` | 4x float32 | Lens calibration / distortion coefficients | Low |
| `1-8-1` | 1061.58 | Focal length in pixels | Medium |
| `1-10-1` | 1000 | IMU sample rate in Hz | Medium (matches 1000 Hz sub-sample math) |
| `1-12-1` | -168 (int64) | Unknown | — |
| `1-13-1` | 4226 (int) | Unknown | — |
| `3-2-5-1` | Always 1.0 | Gain? Aperture ratio? | Low |
| `3-2-16-1` | Always 25.0 | LRF framerate? Target stabilization rate? | Low |
| `3-2-17-1` | 100/1000 = 0.1 | Unknown | — |

**To investigate:** Compare values across multiple OSV files. Fields that stay constant across captures are likely device/config properties. Fields that vary are per-capture settings. `1-3-1` and `1-8-1` are particularly interesting — if these are lens intrinsics, we can use them for fisheye reprojection without DJI Studio.

### 4. `dbgi` debug tracks (streams 5 and 6)

Two `dbgi` tracks at 1.58 Mbps each — the largest metadata streams by far (more than 6x the primary `djmd`). Completely unexplored. Not present in the LRF sidecar.

**To investigate:** Extract with ffmpeg or osvtoolbox, hex-inspect, check for protobuf structure. The high data rate suggests either per-pixel debug info, high-rate raw sensor data, or verbose diagnostic logging. Worth at least a cursory hex dump to characterize.

### 5. `camd` MP4 box (3.2 MB)

ExifTool reports `Unknown camd: (Binary data 3185385 bytes, use -b option to extract)` at the file level. This is a custom DJI MP4 box, not part of the per-frame stream structure.

**To investigate:** `exiftool -b -camd <file>.osv > camd_box.bin`, then hex-inspect. Could contain calibration data, stitching parameters, or a summary of the entire capture session.

### 6. Cross-file comparison

Only one OSV file analyzed so far. The `D:\Capture\` directory has ~20 files across different scenes, dates, and lighting conditions.

**To investigate:**
- Do device fields (serial, firmware, proto version) stay constant across captures from the same camera?
- Do the unknown fields at `1-3-1`, `1-8-1`, etc. vary per-clip or per-device?
- Do any captures have non-zero GPS (were any taken with the remote)?
- Do different capture durations and motion profiles affect the telemetry structure?
- Are the zero-padding patterns at end-of-recording consistent?

### 7. LRF telemetry vs OSV telemetry

The LRF has its own `djmd` tracks at 25fps (2002 frames). The OSV has `djmd` at 50fps (4003 frames). If the LRF quaternions are just every-other-frame from the OSV, then the LRF is a drop-in for fast iteration. If they differ (e.g., post-stitch correction applied to LRF), that's important to know.

**To investigate:** Extract quaternions from both, downsample OSV to 25fps, compute per-frame difference. Should be zero or near-zero if they're the same source.

### 8. Body-frame ERP validation (next pipeline step)

This is the bridge from investigation to application. Apply the inverse per-frame quaternion to the LRF ERP and check whether the camera operator's apparent position stabilizes near the nadir.

**To investigate:**
1. Extract a frame from LRF: `ffmpeg -i file.LRF -vframes 1 -map 0:0 preview_erp.png`
2. Take the corresponding quaternion from telemetry
3. Compute inverse rotation
4. Re-render the ERP sphere with the inverse rotation
5. Compare operator position in gravity-corrected vs body-frame ERP

The LRF is the fast path for this (low-res, already stitched). Full-res validation via DJI Studio export comes after.

---

## Extraction tools

| Tool | Status | What it provides |
|------|--------|-----------------|
| ExifTool v13.41+ | **Working** — used for all extraction so far | Full protobuf decode of `djmd` tracks via `-ee` flag |
| ffprobe | **Working** | Container structure, stream identification |
| ffmpeg | Available | Frame extraction, stream demuxing |
| osvtoolbox | Not installed | Raw track extraction + recomposition. C++17 build required. |
| Telemetry Extractor | Not installed | Commercial GUI, exports CSV/JSON. Useful as ground truth. |
| pyosmogps | Not installed | Python reference for proto parsing patterns (GPS only) |
| telemetry-parser | Not installed | Gyroflow's Rust parser. Has DJI proto definitions. |

---

## Related documents

| Document | Location | Role |
|----------|----------|------|
| Gravity-aware masking plan | [`360_masking_gravity_aware_plan.md`](360_masking_gravity_aware_plan.md) | Parent plan. OSV investigation is Step 0. |
| OSV testing approach | [`OSV_file_testing_approach.md`](OSV_file_testing_approach.md) | Structured test plan used for the first analysis session. Includes pre-research, phase definitions, and results in Section 8. |
| Telemetry report (formal) | [`device_reports/osmo-360/osv-telemetry-2026-04-12/OSV_Telemetry_Report.md`](device_reports/osmo-360/osv-telemetry-2026-04-12/OSV_Telemetry_Report.md) | Detailed findings from the first OSV file. Full statistics, proto field map, quality validation. |
| Telemetry data (JSON) | [`device_reports/osmo-360/osv-telemetry-2026-04-12/telemetry_report.json`](device_reports/osmo-360/osv-telemetry-2026-04-12/telemetry_report.json) | All 4003 per-frame quaternion + accelerometer samples. Powers the HTML dashboard. |
| HTML dashboard | [`device_reports/osmo-360/osv-telemetry-2026-04-12/osv_telemetry_report.html`](device_reports/osmo-360/osv-telemetry-2026-04-12/osv_telemetry_report.html) | Interactive charts for quaternion signals, norms, Euler angles, accelerometer, deltas. |
| Raw extraction outputs | `report_data/osv_ffprobe.json`, `osv_exiftool_metadata.txt`, `osv_telemetry_raw.txt` | Local scratch files (git-ignored). Full ffprobe and exiftool dumps. |
