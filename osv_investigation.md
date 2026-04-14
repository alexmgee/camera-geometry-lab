# OSV Format Investigation

Living investigation document for DJI Osmo 360 `.osv` file analysis. Tracks what we know, what we don't, and what to try next.

**Camera:** DJI Osmo 360 (dual 1"-type sensors, 8K panoramic)
**Started:** 2026-04-12
**Last updated:** 2026-04-13 (corrected per validation review — see [`osv_investigation_validation_response.md`](osv_investigation_validation_response.md))
**Pre-correction version:** [`legacy/osv_investigation_pre_validation.md`](legacy/osv_investigation_pre_validation.md)

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

The `.LRF` file (88 MB) ships alongside every `.osv`. Its container structure:

| Stream | Type | Codec | Content | Per-frame |
|--------|------|-------|---------|-----------|
| 0 | video | H.264 High | 2048x1024, 8-bit, 25fps | 2002 |
| 1 | audio | AAC | 48kHz stereo | 3753 |
| 2 | data | `djmd` | Telemetry at 25fps | 2002 |
| 3 | data | `djmd` | Secondary telemetry at 25fps | 2002 |
| 4 | video | MJPEG | 688x344 thumbnail | 1 |

No `dbgi` tracks in LRF. Half framerate (25fps vs 50fps).

**Important correction:** The LRF video track is **not** a stitched equirectangular. A freshly extracted frame shows a **side-by-side dual-fisheye preview** (two ~1024x1024 fisheye images packed into 2048x1024). The 2:1 aspect ratio was initially misinterpreted as ERP. The actual geometric content is a reduced-resolution preview of the two raw fisheye streams, not a stitched panorama.

The LRF remains useful as:
- a compact telemetry source (first 10 matching timestamps show identical quaternion values to OSV; full-file parity not yet checked)
- a small companion file (88 MB vs 1.7 GB)
- a low-res dual-fisheye preview

It is **not** usable as an ERP input for body-frame rotation or masking validation.

### Protobuf schema

The telemetry self-identifies via ExifTool's `Category` field:

```
pb_file:dvtm_oq101.proto; model_name:OQ001; pb_version:2.0.8; pb_lib_version:02.01.15;
```

ExifTool v13.41+ has built-in decoding support. No custom proto compilation or proprietary tools required.

Schema reference: https://exiftool.org/TagNames/DJI.html (lists `dvtm_oq101.proto` among 15+ DJI camera protos). ExifTool's docs explicitly map field names including `ISO`, `ShutterSpeed`, `ColorTemperature`, `AccelerometerX/Y/Z`, `GPSInfo`, `AbsoluteAltitude`, `GPSDateTime`.

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

Magnitude mean: 1.0045g. Range: 0.74g to 2.32g. Consistent with handheld walking dynamics. Field names confirmed by ExifTool DJI tag documentation.

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

| Proto path | Field | Value | Stability |
|-----------|-------|-------|-----------|
| `1-1-1` | Proto file | dvtm_oq101.proto | Constant (device) |
| `1-1-3` | Proto version | 2.0.7 (pre-update) / 2.0.8 (post-update) | Changes with firmware |
| `1-1-5` | Serial number | 95SXN7S02213TB | Constant (device) |
| `1-1-6` | Firmware | 10.00.14.19 (pre) / 10.00.25.29 (post) | Changes with firmware |
| `1-1-9` | Device ID | varies per session | Per-session counter |
| `1-1-10` | Model | Osmo 360 | Constant (device) |
| `1-11-1` | Framerate | 49.999 | Constant (capture mode) |
| `1-14-2` | Sensor dimension | 3840 | Constant (device) |

Firmware update occurred between Nov 2025 (v10.00.14.19, proto 2.0.7) and Mar 2026 (v10.00.25.29, proto 2.0.8). Confirmed across 3 files spanning 5 months.

### `camd` MP4 box

The `camd` box (3,185,385 bytes) at the end of the OSV container is a **self-contained MP4 file containing only the two `djmd` telemetry tracks** — no video, no audio, no `dbgi`. Same bitrates (255 + 57 kbps), same frame counts (4003), same duration, byte-identical telemetry values. This is DJI's mechanism for tools that want telemetry without parsing the full 1.7 GB file.

Two relevant offsets:
- `0x67aa086e`: start of the `camd` box header
- `0x67aa0876`: start of the embedded MP4 payload inside the box

Extraction requires direct binary read — `exiftool -b` outputs a warning string, not the actual payload. Verified via ffprobe on the extracted payload.

Note: the LRF metadata also reports an embedded `camd` blob, so both OSV and LRF carry nested telemetry payloads.

### Secondary `djmd` track (stream 4)

The secondary `djmd` track (57 kbps, stream 4 in the main container, stream 1 in the `camd` box) is a **lightweight per-frame exposure record**:

- Mostly 142 bytes per frame (3939 packets), with 63 packets at 141 bytes and 1 larger first packet at 310 bytes (header-bearing)
- Mean primary-track packet size: ~637 bytes — secondary is ~4.5x smaller
- 4003 records, one per video frame
- Contains the string "Osmo OQ001" exactly 4003 times (one per frame)
- **Does NOT contain quaternions or accelerometer data**

Per-frame varying fields observed:

| Field | Range (deskTest) | Interpretation |
|-------|-----------------|----------------|
| Float at z#-block offset 1 | 6.41 - 7.20 | EV or gain value |
| Float at z#-block offset 2 | 265.0 - 283.6 | Shutter speed denominator (1/x sec) |
| Varint after `\x32\x03\x08` | 5028 - 5090 | Color temperature or ISO |

Five additional floats per frame are constant (32.0, 32.0, 32.0, 1.0, 1.0). The device header (proto schema, serial, firmware) appears only in the first record.

### Factory lens calibration (proto message `2-6`)

**Major finding.** The primary `djmd` track's message 2 contains **complete factory calibration data for both lenses**, stored as 8 paired calibration sets (front + back). This data appears once in the first frame and is constant. The calibration set IDs are semantically sparse: `1, 2, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24` — not a simple contiguous range.

#### Active calibration (sets 1 and 2)

| Parameter | Front lens (2-6-1) | Back lens (2-6-2) | Unit |
|-----------|-------------------|-------------------|------|
| fx | 1040.156 | 1051.969 | px |
| fy | 1040.187 | 1051.898 | px |
| cx | 1908.603 | 1915.396 | px |
| cy | 1918.948 | 1920.315 | px |
| k1 | 0.07397 | 0.06619 | — |
| k2 | -0.02348 | -0.01113 | — |
| p1 | 0.01884 | 0.00959 | — |
| p2 | -0.00973 | -0.00672 | — |
| Width | 3840 | 3840 | px |
| Height | 3840 | 3840 | px |
| Azimuth | -179.991 | 0.045 | deg |
| Elevation | 90.276 | 90.318 | deg |
| Roll | -0.114 | -0.295 | deg |

Lens separation: 180.036° (azimuth difference), consistent with back-to-back dual-fisheye geometry.

Principal points slightly off-center from 1920: front = (1908.6, 1918.9), back = (1915.4, 1920.3).

Front and back focal lengths differ by ~12 px — each lens is individually calibrated.

#### Extrinsic quaternions (field `-28`)

| Lens | w | x | y | z | Interpretation |
|------|---|---|---|---|----------------|
| Front | -0.000650 | 0.000757 | -0.705404 | 0.708805 | ~90° rotation around Z |
| Back | 0.705141 | 0.709062 | -0.001548 | -0.002098 | ~90° rotation around X |

Both are unit quaternions. These represent the rotation from each lens's sensor frame to the camera body frame.

#### Calibration history (sets 11-24)

7 additional front/back pairs with the same field structure. Focal lengths drift monotonically:

| Lens | fx range across sets | Span |
|------|---------------------|------|
| Front (sets 1,11,13,15,17,19,21,23) | 1036.45 - 1040.91 | 4.5 px |
| Back (sets 2,12,14,16,18,20,22,24) | 1048.30 - 1051.97 | 3.7 px |

Distortion coefficients (k1, k2, p1, p2) are **shared** across sets of the same lens — only focal length, principal point, and extrinsic quaternion vary across pairs. The focal length drift is consistent with temperature-dependent calibration, but the available evidence only proves that multiple persistent calibration states exist — not the specific physical mechanism.

#### Distortion model interpretation

The fields `-1` through `-8` are numerically consistent with the standard **Brown-Conrady / OpenCV convention** (fx, fy, cx, cy, k1, k2, p1, p2), which DJI documents in its DewarpData XMP spec and DJI Terra. No k3 field is present (only 4 distortion coefficients). The small magnitudes of k1/k2 are expected for fisheye lenses where the dominant projection is handled by the fisheye model itself and the polynomial terms are residual corrections.

This interpretation is plausible and strongly supported by the numerical structure, but has not been independently proven from a DJI primary source specific to `dvtm_oq101.proto`. A future parser should preserve the raw field values rather than committing to this mapping prematurely.

#### Distortion lookup tables (fields `-22` and `-23`)

14-entry symmetric float32 arrays, identical across all calibration sets and both lenses:

```
Field -22: [1920.0, 317.9, 518.1, 753.3, 1012.5, 1299.2, 1604.8, 1920.0, 2235.2, 2540.8, 2827.5, 3086.7, 3321.9, 3522.1]
Field -23: [3735.0, 2845.0, 3096.3, 3310.4, 3491.8, 3625.5, 3707.4, 3735.0, 3707.4, 3625.5, 3491.8, 3310.4, 3096.3, 2845.0]
```

Field -22 is symmetric around 1920 (sensor half-width). Field -23 is palindromic. Purpose unknown — not documented in any public DJI source, ExifTool, Gyroflow, or reverse-engineering project. Possibly related to vignetting correction, blend zone definition, or fisheye projection mapping. Not needed for the Brown-Conrady model itself.

#### Ancillary calibration fields

| Field | Value | Notes |
|-------|-------|-------|
| `-24` | 8.0 | Possibly polynomial order |
| `-25` | -1000 | Unknown |
| `-20`, `-21`, `-27` | Paired float64 values | Unknown purpose |

### Sensor hardware

The `dbgi` debug tracks identify the image sensor as **OmniVision OV68A40** — a 1-inch, ~68MP CMOS sensor. DJI uses a 3840x3840 readout (at 50fps, 10-bit) from this sensor per fisheye lens. The debug proto schema is `dbginfo_oq101.proto` v2.0.2, separate from the telemetry proto. Per-frame debug packet size: ~3950 bytes per lens.

### GPS (proto path `3-4`)

ExifTool's DJI tag documentation maps `3-4-2-1` to `GPSInfo`, `3-4-2-2` to `AbsoluteAltitude`, and `3-4-2-6-1` to `GPSDateTime`. ExifTool's documented behavior is that missing numeric protobuf fields default to zero.

No usable GPS data was observed in any analyzed capture (deskTest, ashland, beachevening). The specific GPS subfields do not appear in ExifTool output, which is consistent with default-zero behavior. The DJI Osmo 360 requires its dedicated remote control for GPS — this is consistent with the data but was not independently proven by this investigation.

### Simplest extraction command

```bash
exiftool -ee -a -u -n <file>.osv \
  | grep -E "^(Sample Time|Dvtm oq 101 3-2-9-[1234]|Accelerometer)"
```

---

## Resolved threads

### 1. Secondary `djmd` track (stream 4)

Extracted via ffmpeg from the `camd` box payload (stream 1). The secondary track is a lightweight per-frame exposure record. Contains shutter speed, EV/gain, color temperature/ISO, and a per-frame model identifier ("Osmo OQ001"). Does NOT contain quaternions or accelerometer. See "Secondary `djmd` track" in established facts.

**Remaining question:** Do the LRF's two `djmd` tracks (219 + 29 kbps) have the same primary/secondary split? The bitrate ratio is similar (~4:1).

### 2. High-rate quaternion sub-samples (proto path `3-3-2`)

The high-rate quaternion stream has been fully characterized.

**Structure per video frame (sub-group 1, `3-3-2-1`):**

| Field | Content | Count per frame |
|-------|---------|----------------|
| `-1` | Timestamp (uint64) | 1 |
| `-2` | Sequence index (monotonically incrementing across all frames) | 1 |
| `-3-{1,2,3,4}` | Quaternion sub-samples (w, x, y, z as float32) | ~20 |
| `-4` | Constant float = 12.25 (unknown purpose) | 1 |

**Key facts:**
- 79,616 sub-samples across 4003 frames = 19.9 per frame
- Effective rate: 994.5 Hz (field `1-10-1` = 1000 Hz nominal)
- Sequence indices: 41022 to 45024, one per frame, incrementing by 1
- Sub-samples within each frame show smooth, monotonic quaternion evolution (~1 ms spacing)
- The **per-frame quaternion at `3-2-9` is byte-identical to sub-sample ~6 of ~20** in the same frame's batch — it's an early-window pick, not a midpoint or average

**Sub-group 2 (`3-3-2-2`): initialization buffer only**
- Only 20 quaternion samples total (first frame only, not per-frame)
- Sequence index = 41021 (one before sub-group 1's first index)
- Contains the last ~20 ms of IMU fusion data from before recording started
- NOT a second sensor fusion pipeline — just a lookback buffer

**Practical implications:**
- For standard masking pipeline work, the per-frame quaternion at `3-2-9` is sufficient
- The high-rate data at `3-3-2-1` enables sub-frame interpolation for rolling-shutter correction or higher-precision temporal alignment if ever needed

### 3. Unknown fields (best-effort)

All fields are constant across captures (confirmed via cross-file comparison).

| Proto path | Value | Best interpretation | Confidence |
|-----------|-------|-------------------|------------|
| `1-3-1` | (0.155, 0.137, -0.094, 0.004) | Accelerometer bias/offset (hardware calibration constant, 4 floats) | Medium |
| `1-8-1` | 1061.58 | Design/nominal focal length in px | Medium |
| `1-10-1` | 1000 | IMU fusion rate in Hz | **Confirmed** (79616 sub-samples / 80.06s = 994.5 Hz) |
| `1-12-1` | -168 (int64) | Timing/synchronization offset (unknown units) | Low |
| `1-13-1` | 4226 (int) | Unknown firmware constant | — |
| `3-2-5-1` | Always 1.0 | Gain multiplier or digital zoom (trivial value) | Medium |
| `3-2-16-1` | Always 25.0 | LRF preview framerate (matches LRF's 25fps) | High |
| `3-2-17-1` | 0.1 (rational 100/1000) | Unknown | — |

`1-12-1`, `1-13-1`, and `3-2-17-1` remain genuinely unknown. Their values are constant and don't affect the masking pipeline.

### 4. `dbgi` debug tracks (streams 5 and 6) — characterized

| Property | Value |
|----------|-------|
| Proto schema | `dbginfo_oq101.proto` v2.0.2 |
| Sensor ID | `OV68A40` (OmniVision ~68MP 1-inch CMOS sensor) |
| Mean per-frame size | ~3950 bytes (front), ~3949 bytes (back) |
| LRF presence | None (dbgi tracks are OSV-only) |

Not useful for the masking pipeline. Low priority for further investigation.

### 5. `camd` MP4 box

See "camd MP4 box" in established facts.

### 6. Cross-file comparison

Compared three files spanning 5 months and a firmware update:
- `CAM_20251024183218_0123_D.OSV` from `D:\Capture\beachevening\` (2025-10-24)
- `CAM_20251106130749_0001_D.OSV` from `D:\Capture\ashland\` (2025-11-06)
- `CAM_20260323172324_0023_D.OSV` from `D:\Capture\deskTest\` (2026-03-23)

**Same across all files (factory/device constants):**

| Field | Value | Interpretation |
|-------|-------|----------------|
| Serial | 95SXN7S02213TB | Same camera |
| Field 1-3-1 | (0.155, 0.137, -0.094, 0.004) | Hardware calibration constant |
| Field 1-8-1 | 1061.582 | Nominal focal length (px) |
| Field 1-10-1 | 1000 | IMU fusion rate (Hz) |
| Field 1-11-1 | 49.999 | Video framerate (fps) |
| Field 1-12-1 | -168 | Unknown constant |
| Field 1-13-1 | 4226 | Unknown constant |
| All 2-6 calibration | Byte-identical hash across all three files | Factory lens calibration |

**Changed across files (per-session/firmware):**

| Field | beachevening (Oct 2025) | ashland (Nov 2025) | deskTest (Mar 2026) |
|-------|------------------------|-------------------|-------------------|
| Firmware | 10.00.14.19 | 10.00.14.19 | 10.00.25.29 |
| Proto version | 2.0.7 | 2.0.7 | 2.0.8 |
| Proto lib version | 02.01.13 | 02.01.13 | 02.01.15 |
| Device ID (1-1-9) | 3543001806 | 235820653 | 8548286131 |

**Key conclusion:** Lens calibration is factory-burned and immutable across captures, firmware versions, and time. Device ID changes per session.

### 7. LRF telemetry vs OSV telemetry

**Telemetry equivalence: partially validated.** Spot-check of the first 10 matching timestamps shows byte-identical quaternion values between LRF (25fps) and OSV (50fps, every-other-frame). Strongly suggests the LRF carries a reduced-rate subset of the same orientation stream, but a full-file parity check has not been performed. The claim should be treated as high-confidence but not proven end-to-end.

**Video geometry: invalidated.** The LRF video is a side-by-side dual-fisheye preview, not a stitched ERP. It cannot be used as an ERP input for body-frame rotation. See the corrected LRF section in established facts.

### 9. Lens calibration interpretation

Fields `-1` through `-8` are numerically consistent with Brown-Conrady / OpenCV convention (fx, fy, cx, cy, k1, k2, p1, p2). Plausible and strongly supported by the numerical structure. Not fully proven from a DJI primary source specific to this proto. See established facts for detail.

LUT arrays (fields -22, -23) remain unknown. Not documented anywhere public.

---

## Open threads

### 8. Body-frame ERP validation — NOT YET PROVEN

The previous attempt at body-frame validation was invalidated for two reasons:

1. **Wrong image model.** The LRF frames are side-by-side dual-fisheye, not stitched equirectangular. The rotation script (`make_bodyframe_erp.py`) assumed ERP input. Applying ERP ray math to a dual-fisheye image produces a meaningless warp, not a valid body-frame rotation.

2. **Script inconsistency.** The script computes `r_world_to_body = r_body_to_world.inv()` but never uses that object — the actual mapping call is `r_body_to_world.apply(flat_rays)`. The comment says "inverse" but the code applies the forward rotation. (For correct ERP input, the forward application would actually be the right operation — but the input wasn't ERP.)

The operator clustering measurements from the previous attempt are not reliable evidence.

**What is still believed to be true (from the telemetry side):**
- The quaternions are real, high-quality, and frame-aligned
- Gyroflow docs confirm DJI quaternions represent fused camera orientation
- The quaternion *should* encode the gravity correction rotation

**What needs to happen to actually validate:**
1. Obtain a genuinely stitched ERP — either from DJI Studio export or by stitching the dual fisheyes independently using the `2-6` calibration
2. Apply the quaternion rotation in a correct ERP pipeline with verified rotation direction
3. Check whether the operator stabilizes in the body-frame result

This is the single most important remaining validation for the masking pipeline.

### 10. LRF geometric characterization

The LRF video is 2048x1024 side-by-side dual-fisheye, not ERP. Open questions:

- Is it a simple downscaled preview of the two primary 3840x3840 lens streams (i.e., two ~1024x1024 fisheye hemispheres)?
- Or is it a lightly processed stitch-preview format with partial corrections?
- Does it use the same fisheye projection model as the full-resolution streams?

Answering these would determine whether the LRF can be used for any geometric work (e.g., stitching it ourselves with the `2-6` calibration).

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
| Validation response | [`osv_investigation_validation_response.md`](osv_investigation_validation_response.md) | Independent review that caught the LRF/ERP error and body-frame invalidation. |
| Telemetry report (formal) | [`device_reports/osmo-360/osv-telemetry-2026-04-12/OSV_Telemetry_Report.md`](device_reports/osmo-360/osv-telemetry-2026-04-12/OSV_Telemetry_Report.md) | Detailed findings from the first OSV file. Full statistics, proto field map, quality validation. |
| Telemetry data (JSON) | [`device_reports/osmo-360/osv-telemetry-2026-04-12/telemetry_report.json`](device_reports/osmo-360/osv-telemetry-2026-04-12/telemetry_report.json) | All 4003 per-frame quaternion + accelerometer samples. Powers the HTML dashboard. |
| HTML dashboard | [`device_reports/osmo-360/osv-telemetry-2026-04-12/osv_telemetry_report.html`](device_reports/osmo-360/osv-telemetry-2026-04-12/osv_telemetry_report.html) | Interactive charts for quaternion signals, norms, Euler angles, accelerometer, deltas. |
| Raw extraction outputs | `report_data/osv_ffprobe.json`, `osv_exiftool_metadata.txt`, `osv_telemetry_raw.txt` | Local scratch files (git-ignored). Full ffprobe and exiftool dumps. |
| Pre-correction investigation | [`legacy/osv_investigation_pre_validation.md`](legacy/osv_investigation_pre_validation.md) | Original version before validation corrections. |
