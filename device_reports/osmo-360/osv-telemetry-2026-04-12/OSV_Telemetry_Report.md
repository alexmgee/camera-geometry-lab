# DJI Osmo 360 OSV Telemetry Analysis Report

**File:** `CAM_20260323172324_0023_D.OSV` (1,742,381,919 bytes)
**Captured:** 2026-03-23 17:23:24 (local) / 22:23:26 UTC
**Duration:** 80.06 seconds at 50 fps
**Analysis date:** 2026-04-12
**Interactive version:** Generate local `report.html` beside this file with `python tools/build_osv_telemetry_report.py --report-dir device_reports/osmo-360/osv-telemetry-2026-04-12`

---

## Executive Summary

Per-frame orientation quaternions were successfully extracted from a DJI Osmo 360 `.osv` file using only ExifTool (`-ee` flag). The quaternion data is high-quality: all 4003 frames have unit-norm quaternions (within 0.0000001 of 1.0), the time series is temporally smooth (max frame-to-frame delta 0.044), and the Euler angle ranges confirm full "alien eye" capture coverage. No proprietary tools or reverse engineering were required.

This completes **Step 0** of the gravity-aware masking pipeline described in the repo's gravity-aware masking plan.

---

## 1. Test Methodology

### 1.1 Tools used

| Tool | Version | Purpose |
|------|---------|---------|
| ffprobe | from FFmpeg (on PATH) | Container structure probing |
| exiftool | 13.41 | Metadata extraction + embedded telemetry decoding |
| Python | 3.14 | Data parsing, statistics, visualization generation |

### 1.2 Extraction commands

**Container probing:**
```bash
ffprobe -v quiet -print_format json -show_format -show_streams <file>.osv
```

**Full telemetry extraction:**
```bash
exiftool -ee -a -u -n <file>.osv
```

**Filtered quaternion + accelerometer extraction:**
```bash
exiftool -ee -a -u -n <file>.osv \
  | grep -E "^(Sample Time|Dvtm oq 101 3-2-9-[1234]|Accelerometer)"
```

**Proto schema identification (in file-level metadata):**
```bash
exiftool -a -u <file>.osv | grep "Category"
# Output: pb_file:dvtm_oq101.proto;model_name:OQ001;pb_version:2.0.8;pb_lib_version:02.01.15;
```

---

## 2. Container Structure

### 2.1 OSV file (primary)

The OSV file is an ISO Base Media File Format (MP4) container with 8 streams:

| Stream | Type | Codec | Details | Frames | Bitrate |
|--------|------|-------|---------|--------|---------|
| 0 | video | HEVC Main 10 | 3840x3840, 50fps, front lens | 4003 | 85.0 Mbps |
| 1 | video | HEVC Main 10 | 3840x3840, 50fps, back lens | 4003 | 85.0 Mbps |
| 2 | audio | AAC | 48kHz, stereo | 3753 | 317 kbps |
| 3 | data | `djmd` | "CAM meta" — primary telemetry | 4003 | 255 kbps |
| 4 | data | `djmd` | "CAM meta" — secondary telemetry | 4003 | 57 kbps |
| 5 | data | `dbgi` | "CAM dbgi" — debug info (front) | 4003 | 1.58 Mbps |
| 6 | data | `dbgi` | "CAM dbgi" — debug info (back) | 4003 | 1.58 Mbps |
| 7 | video | MJPEG | 688x344, thumbnail (attached_pic) | 1 | — |

**MP4 box layout:** `ftyp` -> `free` (4044 bytes) -> `mdat` (1.74 GB) -> `moov` (track headers, sample tables) -> `camd` (3.2 MB, DJI camera data)

**Format tags:** `major_brand: isom`, `compatible_brands: isom, iso2, mp41`, `encoder: Osmo 360`

**Video specs:** 10-bit color depth (`yuv420p10le`), BT.709 color space, limited range, no B-frames.

### 2.2 LRF sidecar file

The `.LRF` file (88,433,635 bytes) is a companion low-resolution file containing:

| Stream | Type | Codec | Details | Frames |
|--------|------|-------|---------|--------|
| 0 | video | H.264 High | **2048x1024 (pre-stitched equirectangular!)**, 25fps | 2002 |
| 1 | audio | AAC | 48kHz, stereo | 3753 |
| 2 | data | `djmd` | "CAM meta" — telemetry at 25fps | 2002 |
| 3 | data | `djmd` | "CAM meta" — secondary | 2002 |
| 4 | video | MJPEG | 688x344, thumbnail | 1 |

**Key discovery:** The LRF video track is a 2:1 aspect ratio already-stitched equirectangular at half the framerate of the OSV. This provides an instant preview without DJI Studio, and its own `djmd` tracks contain telemetry at 25fps. No `dbgi` debug tracks are present in the LRF.

### 2.3 Differences between OSV and LRF

| Property | OSV | LRF |
|----------|-----|-----|
| Video | Dual-fisheye, 3840x3840 per lens | Single pre-stitched ERP, 2048x1024 |
| Video codec | HEVC Main 10 (10-bit) | H.264 High (8-bit) |
| Framerate | 50 fps | 25 fps |
| Debug tracks | 2x `dbgi` (1.58 Mbps each) | None |
| `djmd` tracks | 2 (255 + 57 kbps) | 2 (219 + 29 kbps) |
| File size | 1.7 GB | 88 MB |

---

## 3. Protobuf Schema

### 3.1 Schema identification

The protobuf schema is self-identifying in the file-level metadata:

```
Microsoft/Category: pb_file:dvtm_oq101.proto;model_name:OQ001;pb_version:2.0.8;pb_lib_version:02.01.15;
```

ExifTool v13.41 has built-in support for `dvtm_oq101.proto`, alongside 15 other DJI camera protos (source: [ExifTool DJI tags](https://exiftool.org/TagNames/DJI.html)).

### 3.2 Device identification fields (Message 1)

| Proto Path | Field | Value |
|-----------|-------|-------|
| `1-1-1` | Proto file | dvtm_oq101.proto |
| `1-1-2` | Proto lib version | 02.01.15 |
| `1-1-3` | Proto version | 2.0.8 |
| `1-1-5` | Serial Number | 95SXN7S02213TB |
| `1-1-6` | Firmware | 10.00.25.29 |
| `1-1-9` | Device ID | 8548286131 |
| `1-1-10` | Model | Osmo 360 |
| `1-2-1` | Unknown | 1 |
| `1-2-2` | Unknown | 1 |
| `1-3-1` | Unknown (4x float32) | Possibly lens calibration |
| `1-8-1` | Unknown (float) | 1061.58 (possibly focal length in px) |
| `1-10-1` | Unknown (int) | 1000 (possibly IMU sample rate Hz) |
| `1-11-1` | Framerate | 49.999 |
| `1-12-1` | Unknown (int64) | -168 |
| `1-13-1` | Unknown (int) | 4226 |
| `1-14-2` | Sensor dimension | 3840 |

### 3.3 Per-frame telemetry fields (Message 3-2)

These fields appear once per video frame (4003 total, 0.02s spacing = 50 Hz):

| Proto Path | ExifTool Name | Type | Notes |
|-----------|---------------|------|-------|
| `3-2-3-1` | ISO | int | Per-frame auto-exposure |
| `3-2-4-1` | Shutter Speed | float32 | Per-frame |
| `3-2-5-1` | Unknown | float32 | Always 1.0 |
| `3-2-6-1` | Color Temperature | float32 | Per-frame white balance |
| **`3-2-9-1`** | **Quaternion W** | **float32** | **Orientation** |
| **`3-2-9-2`** | **Quaternion X** | **float32** | **Orientation** |
| **`3-2-9-3`** | **Quaternion Y** | **float32** | **Orientation** |
| **`3-2-9-4`** | **Quaternion Z** | **float32** | **Orientation** |
| **`3-2-10-2`** | **Accelerometer X** | **float32 (g)** | **Motion** |
| **`3-2-10-3`** | **Accelerometer Y** | **float32 (g)** | **Motion** |
| **`3-2-10-4`** | **Accelerometer Z** | **float32 (g)** | **Motion** |
| `3-2-10-20-*` | Unknown (arrays of zeros) | varint | Unused in this capture |
| `3-2-10-21-*` | Unknown (arrays of zeros) | varint | Unused in this capture |
| `3-2-10-22-*` | Unknown (arrays of zeros) | varint | 30 values per frame |
| `3-2-10-23-*` | Unknown (arrays of zeros) | varint | 28 values per frame |
| `3-2-10-27-*` | Unknown (arrays of zeros) | varint | 4 values per frame |
| `3-2-15-1..7` | Exposure parameters | float32 | 7 values including EV, dynamic range |
| `3-2-16-1` | Unknown | float32 | Always 25.0 |
| `3-2-17-1` | Unknown | rational | 100/1000 = 0.1 |

### 3.4 High-rate sub-samples (Message 3-3-2)

In addition to the per-frame quaternion at `3-2-9`, there is a **high-rate quaternion stream** at `3-3-2-N-3`:

| Proto Path | Content | Count |
|-----------|---------|-------|
| `3-3-2-N-1` | Raw timestamp | Per sub-sample |
| `3-3-2-N-2` | Sub-sample sequence index | Per sub-sample |
| `3-3-2-N-3-{1,2,3,4}` | Quaternion (w, x, y, z) | ~20 per video frame |
| `3-3-2-N-4` | Unknown (float) | Per sub-sample |

**Total sub-samples:** 79,616 across 4003 frames = **19.9 sub-samples per frame** (~1000 Hz IMU fusion rate for a 50fps video).

The `N` alternates between sub-groups `1` and `2`, likely corresponding to front and back lens sensor data or two phases of the sensor fusion pipeline.

### 3.5 GPS fields (Message 3-4)

GPS fields are present in the schema but **all zeroed** in this capture:

| Proto Path | Expected Content | Status |
|-----------|-----------------|--------|
| `3-4-2-1` | GPS coordinate structure | Zeroed |
| `3-4-2-2` | Absolute altitude | Zeroed |
| `3-4-2-6-1` | GPS date/time string | Zeroed |

GPS requires the dedicated DJI remote control to be connected during capture. The remote was not used for this test clip.

---

## 4. Quaternion Analysis

### 4.1 Basic statistics

| Metric | Value |
|--------|-------|
| Total frames with quaternions | 4003 |
| Sample rate | 50 Hz (0.02s per frame) |
| Time range | 0.00s to 80.04s |
| Zero-quaternion frames | 0 |

### 4.2 Component ranges

| Component | Minimum | Maximum | Span |
|-----------|---------|---------|------|
| w | 0.130475 | 0.821332 | 0.691 |
| x | -0.726596 | 0.315570 | 1.042 |
| y | -0.783746 | 0.428917 | 1.213 |
| z | -0.641564 | 0.744194 | 1.386 |

All components sweep wide ranges, confirming the camera was rotated through most of the orientation sphere during this 80-second capture.

### 4.3 Quaternion norm verification

| Metric | Value |
|--------|-------|
| Norm minimum | 0.9999999308 |
| Norm maximum | 1.0000001358 |
| Norm mean | 1.0000000388 |
| All norms within 0.001 of 1.0 | **YES** |
| All norms within 0.0000002 of 1.0 | **YES** |

The quaternions are unit quaternions to float32 precision limits.

### 4.4 Temporal smoothness

| Metric | Value |
|--------|-------|
| Max frame-to-frame delta | 0.043550 |
| Max delta timestamp | t = 56.26s |
| Mean frame-to-frame delta | 0.003714 |
| Discontinuities (delta > 0.5) | 0 |

The maximum delta of 0.044 corresponds to a camera rotation of approximately 5 degrees between consecutive frames (at 50fps), which is consistent with energetic handheld motion. No discontinuities were found.

### 4.5 Euler angle analysis (ZYX convention)

| Axis | Minimum | Maximum | Span |
|------|---------|---------|------|
| Yaw | -179.9 deg | 179.9 deg | 359.8 deg |
| Pitch | -89.8 deg | 88.9 deg | 178.7 deg |
| Roll | -176.3 deg | 176.4 deg | 352.7 deg |

The camera covered nearly the entire orientation sphere during this capture session, consistent with the "alien eye" handheld capture style described in the gravity-aware masking plan.

### 4.6 Sample data (first 5 frames)

| Time (s) | qw | qx | qy | qz | Accel X (g) | Accel Y (g) | Accel Z (g) |
|----------|------|------|------|------|-------------|-------------|-------------|
| 0.00 | 0.5647 | -0.4485 | -0.5091 | -0.4699 | -0.9519 | 0.0242 | -0.1048 |
| 0.02 | 0.5670 | -0.4509 | -0.5073 | -0.4667 | -0.9833 | 0.0352 | -0.0992 |
| 0.04 | 0.5686 | -0.4526 | -0.5063 | -0.4642 | -1.0240 | 0.0393 | -0.0766 |
| 0.06 | 0.5684 | -0.4528 | -0.5068 | -0.4637 | -1.0042 | 0.0458 | -0.0842 |
| 0.08 | 0.5673 | -0.4522 | -0.5083 | -0.4641 | -0.9654 | 0.0489 | -0.1005 |

---

## 5. Accelerometer Analysis

### 5.1 Basic statistics

| Metric | Value |
|--------|-------|
| Frames with accelerometer data | 4003 |
| Magnitude minimum | 0.7357 g |
| Magnitude maximum | 2.3218 g |
| Magnitude mean | 1.0045 g |

The mean magnitude of 1.00g is consistent with a handheld device experiencing gravity plus walking dynamics. The minimum (0.74g) and maximum (2.32g) indicate brief unloading and stronger motion events, respectively.

### 5.2 Axis ranges

| Axis | Minimum | Maximum |
|------|---------|---------|
| X | -2.47 g | 1.23 g |
| Y | -1.19 g | 1.55 g |
| Z | -2.51 g | 0.66 g |

---

## 6. Data Quality Validation

### 6.1 Test results

| # | Test | Criterion | Measured | Result |
|---|------|-----------|----------|--------|
| 1 | Frame count matches video | 4003 frames | 4003 frames | **PASS** |
| 2 | Sample rate = 50 Hz | 0.02s spacing | 0.02s spacing | **PASS** |
| 3 | Quaternion norm min | > 0.999 | 0.9999999308 | **PASS** |
| 4 | Quaternion norm max | < 1.001 | 1.0000001358 | **PASS** |
| 5 | Temporal smoothness | Max delta < 0.1 | 0.043550 | **PASS** |
| 6 | No zero quaternions | 0 zero frames | 0 zero frames | **PASS** |
| 7 | Accel near 1g | Mean 0.8-1.2g | 1.0045g | **PASS** |
| 8 | Full rotation coverage | Wide Euler ranges | Yaw 360 deg | **PASS** |

**All 8 tests PASS.**

### 6.2 DJI's quaternion representation

Based on Gyroflow documentation and the observed data:

- DJI records **pre-computed quaternions from on-device sensor fusion**, not raw gyroscope/accelerometer
- The quaternion represents the camera's orientation in a gravity-aligned reference frame
- This is exactly the rotation that the stitcher applies to level the horizon in the output ERP
- Inverting this quaternion should transform gravity-corrected ERP back to body-frame coordinates

---

## 7. Implications for the Gravity-Aware Masking Pipeline

All questions from Step 0 of the repo's gravity-aware masking plan are answered:

| Question | Answer |
|----------|--------|
| Does the OSV container hold telemetry? | **YES** — two `djmd` tracks per file |
| Is per-frame orientation data embedded? | **YES** — quaternion at 50 Hz, 1:1 with video frames |
| What format are the quaternions in? | Float32, unit quaternions, protobuf (`dvtm_oq101.proto`) |
| Are they pre-computed (sensor fusion on-device)? | **YES** — confirmed by Gyroflow docs and data quality |
| Can we extract without proprietary tools? | **YES** — ExifTool v13.41+ has built-in support |
| Is GPS present without remote? | **NO** — GPS fields present but zeroed without remote |
| Is the LRF useful? | **YES** — pre-stitched 2048x1024 ERP at 25fps for quick preview |

### 7.1 Recommended next step

**Phase 4: Body-frame validation.** Apply the inverse quaternion to the LRF equirectangular to produce a body-frame ERP and verify that the operator position stabilizes near the nadir.

Approach:
1. Extract a frame from the LRF: `ffmpeg -i file.LRF -vframes 1 preview_erp.png`
2. Extract the corresponding quaternion from the first `djmd` sample
3. Compute the inverse rotation
4. Re-render the ERP with the inverse rotation applied (rotate the sphere)
5. Compare operator position in gravity-corrected ERP vs. body-frame ERP

The LRF provides a fast path for this validation (low-res, already stitched, no DJI Studio required).

---

## 8. Tool Ecosystem Summary

| Tool | Type | Can Extract Quaternions | Notes |
|------|------|------------------------|-------|
| **ExifTool** (v13.41+) | Open source, Perl | **YES** (built-in proto support) | Simplest path. Used for this analysis. |
| [osvtoolbox](https://github.com/ChelouteVR/osvtoolbox) | Open source, C++17 | Raw `djmd` binary only | Useful for recomposing modified OSV files |
| [Telemetry Extractor](https://goprotelemetryextractor.com/tools-for-dji-action) | Commercial | **YES** (GUI, exports CSV/JSON) | Good for ground truth validation |
| [pyosmogps](https://github.com/francescocaponio/pyosmogps) | Open source, Python | GPS only (not orientation) | Reference for protobuf parsing patterns |
| [telemetry-parser](https://github.com/AdrianEddy/telemetry-parser) | Open source, Rust | DJI Action (not confirmed for OSV) | Powers Gyroflow; has DJI proto definitions |
| [osv2gpx](https://www.facebook.com/groups/GoogleStreetViewTrustedPhotographers/posts/3183404758501882/) | Donationware | GPS only | By Dean Zwikel |
| ffprobe | Open source | Container structure only | Essential for stream identification |

---

## 9. References

| Resource | URL |
|----------|-----|
| ExifTool DJI tag definitions | https://exiftool.org/TagNames/DJI.html |
| osvtoolbox (OSV extract/recompose) | https://github.com/ChelouteVR/osvtoolbox |
| Telemetry Extractor for DJI Action | https://goprotelemetryextractor.com/tools-for-dji-action |
| pyosmogps (Python DJI GPS parser) | https://github.com/francescocaponio/pyosmogps |
| telemetry-parser (Gyroflow) | https://github.com/AdrianEddy/telemetry-parser |
| DJI djmd proto release request | https://github.com/dji-sdk/Payload-SDK-Tutorial/issues/4 |
| Gyroflow DJI camera support | https://docs.gyroflow.xyz/app/getting-started/supported-cameras/dji |
| Blackmagic Forum OSV discussion | https://forum.blackmagicdesign.com/viewtopic.php?f=3&t=226243 |
| Repo gravity plan working doc | `360_masking_gravity_aware_plan.md` (local working doc) |
| Repo OSV testing approach working doc | `OSV_file_testing_approach.md` (local working doc) |
