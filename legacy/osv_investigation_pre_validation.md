# OSV Format Investigation

Living investigation document for DJI Osmo 360 `.osv` file analysis. Tracks what we know, what we don't, and what to try next.

**Camera:** DJI Osmo 360 (dual 1"-type sensors, 8K panoramic)
**Started:** 2026-04-12
**Last updated:** 2026-04-13 (session 2: all threads resolved)

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

Found by binary scan at file offset `0x67aa086e`. Starts with its own `ftyp` box, contains `mdat` + `moov` with two `djmd` tracks. Verified via ffprobe and by extracting quaternions from the embedded MP4 and comparing to the main container.

### Secondary `djmd` track (stream 4)

The secondary `djmd` track (57 kbps, stream 4 in the main container, stream 1 in the `camd` box) is a **lightweight per-frame exposure record**:

- Fixed 141 bytes per frame (vs ~638 bytes avg for primary track)
- 4003 records, one per video frame
- Contains the string "Osmo OQ001" per frame (model identifier)
- **Does NOT contain quaternions or accelerometer data**

Per-frame varying fields observed:

| Field | Range (deskTest) | Interpretation |
|-------|-----------------|----------------|
| Float at z#-block offset 1 | 6.41 - 7.20 | EV or gain value |
| Float at z#-block offset 2 | 265.0 - 283.6 | Shutter speed denominator (1/x sec) |
| Varint after `\x32\x03\x08` | 5028 - 5090 | Color temperature or ISO |

Five additional floats per frame are constant (32.0, 32.0, 32.0, 1.0, 1.0). The device header (proto schema, serial, firmware) appears only in the first record.

### Factory lens calibration (proto message `2-6`)

**Major finding.** The primary `djmd` track's message 2 contains **complete factory calibration data for both lenses**, stored as 8 paired calibration sets (front + back). This data appears once in the first frame and is constant.

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

Likely represents temperature-dependent calibration or calibration history. Distortion coefficients (k1, k2, p1, p2) are **shared** across sets of the same lens — only focal length, principal point, and extrinsic quaternion vary.

#### Distortion lookup tables (fields `-22` and `-23`)

14-entry symmetric float32 arrays, identical across all calibration sets and both lenses:

```
Field -22: [1920.0, 317.9, 518.1, 753.3, 1012.5, 1299.2, 1604.8, 1920.0, 2235.2, 2540.8, 2827.5, 3086.7, 3321.9, 3522.1]
Field -23: [3735.0, 2845.0, 3096.3, 3310.4, 3491.8, 3625.5, 3707.4, 3735.0, 3707.4, 3625.5, 3491.8, 3310.4, 3096.3, 2845.0]
```

Field -22 is symmetric around 1920 (sensor half-width). Field -23 is palindromic. Together they likely define a radial mapping for fisheye projection/unprojection.

### Sensor hardware

The `dbgi` debug tracks identify the image sensor as **OmniVision OV68A40** — a 1-inch, ~68MP CMOS sensor. DJI uses a 3840x3840 readout (at 50fps, 10-bit) from this sensor per fisheye lens. The debug proto schema is `dbginfo_oq101.proto` v2.0.2, separate from the telemetry proto.

### GPS (proto path `3-4`)

GPS fields exist in the schema but are **all zeroed** across all analyzed captures (deskTest, ashland, beachevening). None were taken with the DJI remote control connected. Fields: `3-4-2-1` (coordinates), `3-4-2-2` (altitude), `3-4-2-6-1` (date/time string).

### Simplest extraction command

```bash
exiftool -ee -a -u -n <file>.osv \
  | grep -E "^(Sample Time|Dvtm oq 101 3-2-9-[1234]|Accelerometer)"
```

---

## Open threads

### ~~1. Secondary `djmd` track (stream 4)~~ RESOLVED

Extracted via ffmpeg from the `camd` box payload (stream 1). The secondary track is a lightweight per-frame exposure record (141 bytes/frame, fixed size). Contains shutter speed, EV/gain, color temperature/ISO, and a per-frame model identifier ("Osmo OQ001"). Does NOT contain quaternions or accelerometer. See "Secondary `djmd` track" in established facts.

**Remaining question:** Do the LRF's two `djmd` tracks (219 + 29 kbps) have the same primary/secondary split? The bitrate ratio is similar (~4:1).

### ~~2. High-rate quaternion sub-samples (proto path `3-3-2`)~~ RESOLVED

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
- Different quaternion values from sub-group 1 (slightly earlier in time)
- NOT a second sensor fusion pipeline — just a lookback buffer

**Practical implications:**
- For standard masking pipeline work, the per-frame quaternion at `3-2-9` is sufficient
- The high-rate data at `3-3-2-1` enables sub-frame interpolation for rolling-shutter correction or higher-precision temporal alignment if ever needed
- No additional extraction tools are required — ExifTool reads the full sub-sample stream

### ~~3. Unknown fields~~ RESOLVED (best-effort)

All fields are constant across captures (confirmed via cross-file comparison, Thread 6).

| Proto path | Value | Best interpretation | Confidence |
|-----------|-------|-------------------|------------|
| `1-3-1` | (0.155, 0.137, -0.094, 0.004) | Accelerometer bias/offset (hardware calibration constant, 4 floats) | Medium |
| `1-8-1` | 1061.58 | Design/nominal focal length in px. Close to equidistant model: f = 1920 / (100° in rad) ≈ 1100 px | Medium |
| `1-10-1` | 1000 | IMU fusion rate in Hz | **Confirmed** (79616 sub-samples / 80.06s = 994.5 Hz) |
| `1-12-1` | -168 (int64) | Timing/synchronization offset (unknown units) | Low |
| `1-13-1` | 4226 (int) | Unknown firmware constant | — |
| `3-2-5-1` | Always 1.0 | Gain multiplier or digital zoom (trivial value) | Medium |
| `3-2-16-1` | Always 25.0 | LRF preview framerate (matches LRF's 25fps) | High |
| `3-2-17-1` | 0.1 (rational 100/1000) | Unknown | — |

`1-12-1`, `1-13-1`, and `3-2-17-1` remain genuinely unknown. Their values are constant and don't affect the masking pipeline.

### 4. `dbgi` debug tracks (streams 5 and 6) — characterized

Extracted front lens `dbgi` track (stream 5) via ffmpeg. Key findings:

| Property | Value |
|----------|-------|
| Proto schema | `dbginfo_oq101.proto` v2.0.2 |
| Sensor ID | `OV68A40` (OmniVision ~68MP 1-inch CMOS sensor) |
| Per-frame size | ~3950 bytes (fixed) |
| Byte entropy | 5.48 bits (structured protobuf, not compressed) |
| Total size | 15.8 MB (front), ~15.8 MB (back) |
| LRF presence | None (dbgi tracks are OSV-only) |

The dbgi data is per-frame sensor diagnostic information — likely register dumps, AE/AWB metering state, ISP pipeline parameters. Not useful for the masking pipeline but confirms the sensor hardware. The `OV68A40` sensor identification is new information.

**Not further investigated.** Parsing would require the `dbginfo_oq101.proto` schema (ExifTool may or may not support it). Low priority for current work.

### ~~5. `camd` MP4 box~~ RESOLVED

The `camd` box is a self-contained MP4 containing only the two `djmd` telemetry tracks. See "camd MP4 box" in established facts.

Extraction method: binary scan for `camd` at file offset `0x67aa086e`, extract payload (box size - 8 header bytes). The `exiftool -b` approach outputs a warning string, not binary data — direct binary extraction is required.

### ~~6. Cross-file comparison~~ RESOLVED (core questions answered)

Compared three files spanning 5 months and a firmware update: beachevening (2025-10-24), ashland (2025-11-06), deskTest (2026-03-23).

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
| All 2-6 calibration | Byte-identical | Factory lens calibration |

**Changed across files (per-session/firmware):**

| Field | beachevening (Oct 2025) | ashland (Nov 2025) | deskTest (Mar 2026) |
|-------|------------------------|-------------------|-------------------|
| Firmware | 10.00.14.19 | 10.00.14.19 | 10.00.25.29 |
| Proto version | 2.0.7 | 2.0.7 | 2.0.8 |
| Proto lib version | 02.01.13 | 02.01.13 | 02.01.15 |
| Device ID (1-1-9) | 3543001806 | 235820653 | 8548286131 | 

Firmware updated between Nov 2025 and Mar 2026. Device ID changes per session (session counter or recording index).

**GPS:** No captures had non-zero GPS data. All used the camera without the remote control.

**Key conclusion:** Lens calibration is factory-burned and immutable. The 8 calibration pairs are shipped with the camera, not generated per-session. Any tool that reads the calibration from one OSV file gets the authoritative values for this specific camera unit.

**Remaining:** Telemetry structure comparison (do proto v2.0.7 files have the same per-frame fields?), comparison across different capture modes (resolution, framerate settings).

### ~~7. LRF telemetry vs OSV telemetry~~ RESOLVED

LRF quaternions are **byte-identical** to the OSV quaternions at matching timestamps. LRF samples at 25fps (0.04s spacing) correspond exactly to every-other-frame from the OSV at 50fps (0.02s spacing). Confirmed by comparing hex values of the first 10 frames.

The LRF is a valid drop-in for quaternion-based workflows requiring fast iteration. Its 2048x1024 pre-stitched ERP video + matching telemetry makes it the ideal fast path for body-frame validation (Thread 8).

### ~~9. Lens calibration interpretation~~ RESOLVED

**Distortion model confirmed:** DJI uses the standard **Brown-Conrady / OpenCV convention** (documented in DJI's DewarpData XMP spec, DJI Terra, and the dji-dewarp project). Fields `-1` through `-8` map directly to: fx, fy, cx, cy, k1, k2, p1, p2. No k3 is present (only 4 distortion coefficients). The small magnitudes (k1 ~0.07) are expected — these are fisheye lenses where the dominant projection is handled by the fisheye model itself, and the Brown-Conrady terms are residual corrections.

**Extrinsics:** Fields `-12`, `-13`, `-14` are Euler angles (azimuth, elevation, roll) and fields `-28-{1..4}` provide the equivalent rotation as a quaternion. Both representations are confirmed by the front/back lens geometry: front azimuth ≈ -180°, back azimuth ≈ 0°, both elevations ≈ 90°.

**8 calibration pairs:** Factory-burned (identical across captures spanning 5 months + firmware update, per Thread 6). The focal length drift across pairs (3.7-4.5 px span) is consistent with temperature-dependent calibration. Distortion coefficients are shared within each lens — only focal length, principal point, and extrinsic quaternion vary across pairs.

**LUT arrays (fields -22, -23):** Purpose unknown. Not documented in any public DJI source, ExifTool, Gyroflow, or reverse-engineering projects examined. The arrays are shared across all calibration sets and both lenses. They are not needed for the Brown-Conrady model itself. Likely related to the stitching pipeline (vignetting correction, blend zone definition, or fisheye projection LUT).

**Ancillary fields:** `-24` = 8.0 (possibly polynomial order), `-25` = -1000 (unknown), `-20`/`-21`/`-27` are paired float64 values of unknown purpose.

**Practical conclusion:** The confirmed Brown-Conrady intrinsics + extrinsic quaternions are sufficient for reprojection and independent stitching. The unknown LUT arrays would only matter for pixel-exact reproduction of DJI Studio's stitch output.

### ~~8. Body-frame ERP validation~~ RESOLVED — rotation works

Applied the inverse per-frame quaternion to LRF ERP frames at 5 timestamps (t=0, 10, 20, 40, 60s). The camera operator's apparent position **does stabilize** in body-frame coordinates.

**Method:** For each pixel in the output (body-frame) ERP, rotate its ray direction by the telemetry quaternion Q (body-to-world) to find the corresponding direction in the gravity-corrected input ERP, then bilinear-sample. Script at `d:/tmp/bodyframe_test/make_bodyframe_erp.py`.

**Rotation direction verified** by testing three variants:
- **Correct (Q applied to body rays):** operator clusters near (x≈1500-1650, y≈700-780) in 2048x1024 px
- **World-frame (no rotation):** operator wanders (x=480-1550, y=580-680) — 339 px mean spread
- **Wrong direction (Q⁻¹ applied):** operator scatters even more (x=200-1750)

Spread ordering: wrong > world > body-frame, confirming the telemetry quaternion represents body-to-world rotation and our inverse is correct.

**Quantitative result (deskTest alien-eye capture):**

| Metric | World-frame | Body-frame | Improvement |
|--------|------------|------------|-------------|
| Mean distance from centroid | 339 px | 186 px | 1.8x |
| Max distance from centroid | 846 px | 458 px | 1.8x |

**Observations:**
- The 1.8x improvement is modest because this is an alien-eye desk capture where the operator's physical direction relative to the camera body varies with stick angle.
- For a rigid-pole or selfie-stick walking capture, the improvement should be much larger (operator locked near nadir).
- The operator's body-frame position (right side of ERP, ≈90-120° from center) is consistent with holding the camera off to one side during a desk test — not below on a stick.
- The black vertical bands in body-frame images are the dual-fisheye stitch seam, which becomes visible after rotation because DJI's stitching is optimized for the gravity-corrected orientation.

**What this means for the masking pipeline:**
- Stage A (quaternion extraction) and Stage B (body-frame ERP) are proven to work.
- The LRF sidecar provides a fast path for body-frame analysis without DJI Studio.
- For walking captures on a selfie stick, body-frame masking should be highly effective — the operator will cluster tightly near a single direction.
- The stitch seam artifacts in body-frame need consideration: masking should happen on the body-frame ERP, but the mask may need to account for seam regions where the operator could be partially erased by DJI's invisible-stick algorithm.

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
| Telemetry report (formal) | [`device_reports/osmo-360/osv-telemetry-2026-04-12/OSV_Telemetry_Report.md`](device_reports/osmo-360/osv-telemetry-2026-04-12/OSV_Telemetry_Report.md) | Detailed findings from the first OSV file. Full statistics, proto field map, quality validation. |
| Telemetry data (JSON) | [`device_reports/osmo-360/osv-telemetry-2026-04-12/telemetry_report.json`](device_reports/osmo-360/osv-telemetry-2026-04-12/telemetry_report.json) | All 4003 per-frame quaternion + accelerometer samples. Powers the HTML dashboard. |
| HTML dashboard | [`device_reports/osmo-360/osv-telemetry-2026-04-12/osv_telemetry_report.html`](device_reports/osmo-360/osv-telemetry-2026-04-12/osv_telemetry_report.html) | Interactive charts for quaternion signals, norms, Euler angles, accelerometer, deltas. |
| Raw extraction outputs | `report_data/osv_ffprobe.json`, `osv_exiftool_metadata.txt`, `osv_telemetry_raw.txt` | Local scratch files (git-ignored). Full ffprobe and exiftool dumps. |
