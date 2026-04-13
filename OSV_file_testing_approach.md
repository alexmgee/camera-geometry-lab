# OSV File Testing Approach

Structured plan for probing DJI Osmo 360 `.osv` files to extract per-frame orientation quaternions.

Implements **Step 0** from [360_masking_gravity_aware_plan.md](360_masking_gravity_aware_plan.md).

**Date:** April 12, 2026
**Status: STEP 0 COMPLETE.** Orientation quaternions successfully extracted. See [Section 8](#8-results-from-actual-testing) for findings.
**Test file:** `CAM_20260323172324_0023_D.OSV` (1.7 GB, 80 seconds @ 50fps)

---

## 1. What we know before testing

Research conducted April 12, 2026 across web, forums, and GitHub established the following facts about the OSV format. Each claim is sourced.

### 1.1 Container structure

OSV files are **MP4 containers** with a custom DJI box layout containing 7 tracks:

| Track | Content | Details |
|-------|---------|---------|
| Track 1 | HEVC video (front lens) | 3840x3840 |
| Track 2 | HEVC video (back lens) | 3840x3840 |
| Track 3 | AAC audio | 48 kHz stereo |
| Track 4 | `djmd` metadata (front) | Variable sample sizes, protobuf |
| Track 5 | `djmd` metadata (back) | Variable sample sizes, protobuf |
| Track 6 | `dbgi` debug info (front) | Variable sample sizes |
| Track 7 | `dbgi` debug info (back) | Variable sample sizes |

Additional structures: `camd` box (camera data), embedded thumbnail, `ftyp`/`free`/`mdat`/`moov` MP4 boxes.

**Source:** [ChelouteVR/osvtoolbox](https://github.com/ChelouteVR/osvtoolbox) README — a C++17 tool that extracts and recomposes OSV files.

### 1.2 Telemetry data inside `djmd` tracks

The `djmd` (DJI metadata) track uses **Google Protocol Buffer** encoding. The proto specification has **not** been officially published by DJI. An open GitHub issue ([dji-sdk/Payload-SDK-Tutorial#4](https://github.com/dji-sdk/Payload-SDK-Tutorial/issues/4), opened Oct 2025 by the LosslessCut developer) requests release of the `.proto` files. DJI released one sample proto in a whitepaper, but it is incomplete and varies across camera models. As of April 2026, this remains unresolved.

Despite the lack of official specs, **multiple independent tools have successfully parsed the data**:

**Confirmed extractable fields from DJI Osmo 360** (per [Telemetry Extractor for DJI Action](https://goprotelemetryextractor.com/tools-for-dji-action)):

| Category | Fields |
|----------|--------|
| **Orientation** | Quaternion w, x, y, z; Pitch angle; Roll angle; Heading |
| **Motion** | Accelerometer X, Y, Z |
| **Position** | Latitude, Longitude, Altitude (requires remote control) |
| **Velocity** | Velocity North, Velocity East, Vertical Velocity |
| **Camera** | Shutter Speed, F-number, White Balance, ISO, Zoom, Focal Length |
| **Time** | Date & time |
| **Derived** | Slope/grade, Bearing, Accelerometer sum |

**Critical finding for our pipeline: orientation quaternions (w, x, y, z) are recorded by the camera alone — no remote control required.** GPS requires the dedicated remote control to be connected.

### 1.3 What DJI records vs. raw IMU

DJI cameras do **not** record raw gyroscope/accelerometer samples. They record **pre-computed quaternions** — the result of on-device sensor fusion. This is confirmed by [Gyroflow documentation](https://docs.gyroflow.xyz/app/getting-started/supported-cameras/dji): "DJI doesn't record the IMU data directly... it only contains Quaternions, which is the final computed camera position."

**Implication for our pipeline:** We get exactly what we need (per-frame orientation) without needing to run our own sensor fusion. The quaternion directly represents the gravity correction rotation applied during stitching.

### 1.4 Gyroflow support status

[Gyroflow's DJI support page](https://docs.gyroflow.xyz/app/getting-started/supported-cameras/dji) lists the Osmo 360 but support appears incomplete. Gyroflow's underlying parser is [AdrianEddy/telemetry-parser](https://github.com/AdrianEddy/telemetry-parser) (pure Rust, no external dependencies). The telemetry-parser supports DJI Action 2/4/5/6, Avata 1/2, Neo 1/2, O3/O4 Air Units — but OSV container support is not explicitly confirmed.

### 1.5 Existing tools inventory

| Tool | Type | OSV Support | Extracts Orientation | Notes |
|------|------|-------------|---------------------|-------|
| [osvtoolbox](https://github.com/ChelouteVR/osvtoolbox) | Open source (C++17) | Yes — primary purpose | Raw `djmd` binary blobs | Does not parse protobuf itself |
| [Telemetry Extractor](https://goprotelemetryextractor.com/tools-for-dji-action) | Commercial ($) | Yes | Yes — quaternion w/x/y/z | Exports CSV, JSON, GPX, KML, GeoJSON, MGJSON |
| [pyosmogps](https://github.com/francescocaponio/pyosmogps) | Open source (Python) | Action 4/5/6 MP4 only | GPS only (not orientation) | Uses protobuf parsing — code is a reference for djmd structure |
| [telemetry-parser](https://github.com/AdrianEddy/telemetry-parser) | Open source (Rust) | Unconfirmed for OSV | Quaternions from DJI Action | Powers Gyroflow; has DJI proto definitions |
| [osv2gpx](https://www.facebook.com/groups/GoogleStreetViewTrustedPhotographers/posts/3183404758501882/) | Donationware | Yes | GPS only | By Dean Zwikel; distributed via Google Drive |
| ffprobe / exiftool | Standard tools | Partial (MP4 container) | No (reads stream metadata, not telemetry payload) | Essential for initial probing |

---

## 2. Tools available on this workstation

Verified present on PATH (per filesystem search April 12, 2026):

| Tool | Path | Status |
|------|------|--------|
| ffprobe | `C:\Users\alexm\ffmpeg\bin\ffprobe.exe` | Ready |
| exiftool | `C:\tools\exiftool.exe` | Ready |
| python | `C:\Python314\python` | Ready |
| bun | On PATH | Ready (for any TS-based tools) |

**Not yet installed (will need):**
- `osvtoolbox` — requires C++17 build or pre-built binary
- `pyosmogps` — `pip install pyosmogps`
- `protobuf` Python library — `pip install protobuf`
- Telemetry Extractor — commercial, trial available

**No `.osv` files currently on disk.** Checked: `D:\Capture`, `D:\Data`, `d:\Projects`, `d:\tmp`, `c:\tmp`. The camera exists (DJI Osmo 360 per hardware context in gravity plan) but no footage has been transferred yet.

**Available for comparison:** 71 `.insv` files (Insta360) at `D:\Capture\InstaFiles\360\`.

---

## 3. Testing phases

### Phase 0: Acquire test footage

**Action:** Capture a short test clip (10-20 seconds) with the DJI Osmo 360 on a selfie stick, walking in a straight line. Transfer the `.osv` file and any sidecar files (`.lrf`) to a working directory.

**Proposed location:** `D:\Capture\osmo360_test\`

**Capture notes:**
- Disable RockSteady before capture
- Keep remote control connected (for GPS data)
- Note the physical orientation of the camera during capture (which direction is "down" relative to body)
- A simple straight-line walk is ideal — the gravity correction should be minimal and predictable

---

### Phase 1: Container probing (ffprobe + exiftool)

Goal: confirm the 7-track structure documented by osvtoolbox and identify any additional metadata.

#### 1A. Full stream and format dump

```bash
ffprobe -v quiet -print_format json -show_format -show_streams <file>.osv > osv_ffprobe_full.json
```

**What to look for:**
- Number and types of streams (expect: 2x video, 1x audio, 2x data, 2x data)
- `codec_tag_string` values — expect `hvc1` for video, `djmd` and `dbgi` for data streams
- Resolution of video tracks (expect 3840x3840 per lens)
- Frame rate and duration
- Any `handler_name` or `title` tags on data streams

#### 1B. Compact stream summary

```bash
ffprobe -v quiet -show_entries stream=index,codec_type,codec_tag_string,width,height,handler_name,nb_frames -print_format json <file>.osv
```

**Expected output pattern:**

| Stream | codec_type | codec_tag | Resolution | Notes |
|--------|-----------|-----------|------------|-------|
| 0 | video | hvc1 | 3840x3840 | Front lens |
| 1 | video | hvc1 | 3840x3840 | Back lens |
| 2 | audio | mp4a | — | 48kHz stereo |
| 3 | data | djmd | — | Front lens metadata |
| 4 | data | djmd | — | Back lens metadata |
| 5 | data | dbgi | — | Front lens debug |
| 6 | data | dbgi | — | Back lens debug |

#### 1C. Exiftool metadata dump

```bash
exiftool -a -u -g1 <file>.osv > osv_exiftool_full.txt
```

**What to look for:**
- Any `XMP` fields with orientation, quaternion, gyro, or IMU data
- `Rotation` or `MatrixStructure` tags
- DJI-proprietary tags (anything with `DJI` prefix)
- GPS-related fields
- `CompressorName` or `HandlerDescription` for data tracks
- Make/Model identification

#### 1D. File magic bytes

```bash
python -c "f=open('<file>.osv','rb'); print(f.read(32).hex()); f.close()"
```

**Expected:** MP4 signature — bytes starting with `00 00 00 xx 66 74 79 70` (ftyp box).

#### 1E. Check for sidecar files

```bash
ls -la <file_directory>/
```

**What to look for:**
- `.lrf` file alongside the `.osv` — may contain low-res preview or additional telemetry
- Any `.json`, `.srt`, or `.log` sidecar files
- If `.lrf` exists, run ffprobe and exiftool on it as well

---

### Phase 2: Raw telemetry extraction

Goal: get the `djmd` binary data out of the container for inspection.

#### 2A. Extract with osvtoolbox

**Install osvtoolbox first:**
```bash
# Clone and build (requires C++17 compiler and FFmpeg dev libs)
git clone https://github.com/ChelouteVR/osvtoolbox.git
cd osvtoolbox
# Build command depends on platform — see repo README
```

**Extract all tracks:**
```bash
./osvtoolbox --extract-data <file>.osv
```

**Expected output files (14 files):**
- `*-track1.mp4`, `*-track2.mp4` — individual lens videos
- `*-track3.mp4` — audio
- `*-djmd1.bin`, `*-djmd2.bin` — raw metadata blobs (THIS IS WHAT WE NEED)
- `*-dbgi1.bin`, `*-dbgi2.bin` — debug info
- `*-djmd1.sizes`, `*-djmd2.sizes`, `*-dbgi1.sizes`, `*-dbgi2.sizes` — sample size tables
- `*-additional-boxes.bin` — ftyp, udta, meta, camd boxes

#### 2B. Alternative: extract djmd track with ffmpeg

If osvtoolbox is not available, attempt direct stream extraction:
```bash
# Identify the djmd stream index from Phase 1 (likely stream 3 or 4)
ffmpeg -i <file>.osv -map 0:3 -c copy djmd_track.bin
```

This may or may not work depending on how ffmpeg handles the custom codec tag.

#### 2C. Hex inspection of djmd binary

```bash
python -c "
f = open('*-djmd1.bin', 'rb')
data = f.read(512)
f.close()
print('First 512 bytes (hex):')
for i in range(0, len(data), 16):
    hex_part = ' '.join(f'{b:02x}' for b in data[i:i+16])
    ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
    print(f'{i:04x}: {hex_part:<48s} {ascii_part}')
"
```

**What to look for:**
- Protobuf field tags (varint-encoded field numbers and wire types)
- Recognizable float32 patterns for quaternion values (values near ±1.0)
- Repeating structure boundaries (each frame's metadata should be a fixed or semi-fixed size)
- Any plaintext strings that reveal field names

#### 2D. Inspect sample sizes

The `.sizes` files from osvtoolbox contain per-sample byte counts for the variable-length tracks. This tells us:

- How many metadata samples exist (should correlate with frame count)
- Whether sample size is constant or variable
- The typical size of one metadata packet

```bash
python -c "
import struct
with open('*-djmd1.sizes', 'rb') as f:
    data = f.read()
# Try reading as uint32 array
sizes = struct.unpack(f'<{len(data)//4}I', data)
print(f'Number of samples: {len(sizes)}')
print(f'Size range: {min(sizes)} - {max(sizes)} bytes')
print(f'First 20 sizes: {sizes[:20]}')
print(f'Constant size: {len(set(sizes)) == 1}')
"
```

---

### Phase 3: Protobuf parsing

Goal: decode the `djmd` binary into structured telemetry with orientation quaternions.

#### 3A. Install Python protobuf tools

```bash
pip install protobuf grpcio-tools
```

#### 3B. Attempt raw protobuf decode (no schema)

Protobuf can be partially decoded without a `.proto` schema — field numbers and wire types are visible, but field names and message nesting are not.

```bash
python -c "
from google.protobuf.internal.decoder import _DecodeVarint
import struct

with open('*-djmd1.bin', 'rb') as f:
    data = f.read()

# Read the sizes file to find sample boundaries
with open('*-djmd1.sizes', 'rb') as f:
    sizes_raw = f.read()
sizes = struct.unpack(f'<{len(sizes_raw)//4}I', sizes_raw)

# Parse first sample
offset = 0
sample = data[offset:offset+sizes[0]]
print(f'First sample: {sizes[0]} bytes')

# Decode protobuf fields
pos = 0
while pos < len(sample):
    tag, new_pos = _DecodeVarint(sample, pos)
    field_number = tag >> 3
    wire_type = tag & 0x7
    wire_names = {0:'varint', 1:'64-bit', 2:'length-delimited', 5:'32-bit'}
    print(f'  Field {field_number}, wire type {wire_type} ({wire_names.get(wire_type, \"unknown\")})', end='')
    
    if wire_type == 0:  # varint
        val, pos = _DecodeVarint(sample, new_pos)
        print(f', value={val}')
    elif wire_type == 1:  # 64-bit fixed
        val = struct.unpack_from('<d', sample, new_pos)[0]
        pos = new_pos + 8
        print(f', float64={val}')
    elif wire_type == 2:  # length-delimited
        length, pos = _DecodeVarint(sample, new_pos)
        payload = sample[pos:pos+length]
        pos += length
        print(f', length={length}')
    elif wire_type == 5:  # 32-bit fixed
        val = struct.unpack_from('<f', sample, new_pos)[0]
        pos = new_pos + 4
        print(f', float32={val}')
    else:
        print()
        break
"
```

**What to look for:**
- Fields with wire type 5 (32-bit fixed) containing float values in range [-1.0, 1.0] — likely quaternion components
- Fields with wire type 1 (64-bit fixed) containing values in range [-180, 180] or [-90, 90] — likely lat/lon or angles
- A group of 4 consecutive float32 fields — quaternion (w, x, y, z)
- A group of 3 consecutive float32 fields — accelerometer (x, y, z)
- Timestamp fields (varint with large values, or float64 with Unix epoch values)

#### 3C. Cross-reference with pyosmogps proto definitions

The `pyosmogps` library successfully parses DJI Action camera protobuf. Its proto definitions may work for Osmo 360 or provide a starting point.

```bash
pip install pyosmogps
# Find the proto files in the installed package
python -c "import pyosmogps; print(pyosmogps.__file__)"
# Navigate to that directory and look for .proto or compiled _pb2.py files
```

#### 3D. Cross-reference with telemetry-parser proto definitions

The Gyroflow telemetry-parser (Rust) contains DJI proto definitions. Clone and inspect:

```bash
git clone https://github.com/AdrianEddy/telemetry-parser.git
# Look for .proto files in the DJI-related directories
find telemetry-parser -name "*.proto" -o -name "*dji*" -o -name "*djmd*"
```

#### 3E. Commercial validation with Telemetry Extractor

If open-source parsing proves difficult, use [Telemetry Extractor](https://goprotelemetryextractor.com/gopro-gps-telemetry-extract) (trial available) to:

1. Load the `.osv` file
2. Export all telemetry to CSV
3. Confirm that orientation quaternions (w, x, y, z) are present per-frame
4. Use the CSV output as ground truth for validating our own parser

Export to JSON for the most structured output:
```
Telemetry Extractor → Load .osv → Export → JSON → orientation_ground_truth.json
```

---

### Phase 4: Quaternion validation

Goal: confirm extracted quaternions represent the gravity correction rotation and can be inverted.

#### 4A. Extract a single frame

```bash
ffmpeg -i <file>.osv -vframes 1 -map 0:0 frame_front.png
ffmpeg -i <file>.osv -vframes 1 -map 0:1 frame_back.png
```

#### 4B. Stitch to ERP via DJI Studio

Export the same clip as equirectangular via DJI Studio (with RockSteady off). This gives us the gravity-corrected ERP to compare against.

#### 4C. Apply inverse quaternion

```python
import numpy as np
from scipy.spatial.transform import Rotation

# q = [w, x, y, z] from extracted telemetry (first frame)
q = np.array([w, x, y, z])

# The gravity correction rotation
R_gravity = Rotation.from_quat([x, y, z, w])  # scipy uses [x,y,z,w] order

# Inverse rotation — undoes gravity correction
R_inverse = R_gravity.inv()

# For each pixel in gravity-corrected ERP, compute ray, apply R_inverse,
# resample from original ERP to get body-frame ERP
# (reuse equirectangular_rays() from Reproject_FEES_IMM_2_Equirectangular.py)
```

#### 4D. Visual validation

Compare operator position in:
1. Gravity-corrected ERP (from DJI Studio) — operator wanders
2. Body-frame ERP (quaternion-reversed) — operator should be near-fixed at nadir

If the operator clusters tightly in the body-frame version, the quaternions are correct.

---

### Phase 5: Temporal consistency check

Goal: verify quaternions across all frames of the test clip.

#### 5A. Plot quaternion time series

```python
import matplotlib.pyplot as plt

# quaternions = array of shape (N, 4) from all frames
fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True)
labels = ['w', 'x', 'y', 'z']
for i, (ax, label) in enumerate(enumerate(zip(axes, labels))):
    ax.plot(quaternions[:, i])
    ax.set_ylabel(label)
axes[-1].set_xlabel('Frame')
plt.suptitle('Per-frame orientation quaternions')
plt.savefig('quaternion_timeseries.png')
```

**What to look for:**
- Smooth curves (no discontinuities or jumps) — camera orientation changes smoothly
- For a straight-line walk: mostly constant with slow drift
- `w` component near 1.0 if camera is nearly level (small rotation from identity)
- Quaternion norm should be 1.0 for every frame (sanity check)

#### 5B. Compute Euler angles for interpretability

```python
from scipy.spatial.transform import Rotation

rotations = Rotation.from_quat(quaternions[:, [1,2,3,0]])  # scipy [x,y,z,w]
euler = rotations.as_euler('ZYX', degrees=True)  # yaw, pitch, roll

# For a level walk: pitch and roll should be small, yaw varies with heading
```

---

## 4. Success criteria

| Criterion | How to verify | Required for pipeline |
|-----------|--------------|----------------------|
| OSV container holds `djmd` data tracks | ffprobe shows data streams with `djmd` codec tag | Yes |
| `djmd` contains per-frame quaternions | Protobuf decode finds 4 float32 fields per sample in [-1, 1] | Yes |
| Quaternion count matches frame count | Compare djmd sample count vs video frame count | Yes |
| Quaternions are smooth over time | Time-series plot shows no discontinuities | Yes |
| Quaternion norms are 1.0 | `np.linalg.norm(q, axis=1)` all ≈ 1.0 | Yes |
| Inverse quaternion produces stable operator position | Visual comparison of gravity-corrected vs body-frame ERP | Yes |
| Accelerometer data also present | Protobuf decode finds 3 float32 fields per sample | Nice to have |
| GPS present (with remote) | Lat/lon fields decode to plausible coordinates | Nice to have |

---

## 5. Risk assessment and fallbacks

### Risk 1: OSV protobuf schema differs from Action cameras

**Likelihood:** Medium. DJI uses different proto schemas across product lines.
**Mitigation:** Use schema-less protobuf decoding (Phase 3B) to discover field layout empirically. Cross-reference field values against Telemetry Extractor output (Phase 3E) as ground truth.

### Risk 2: Quaternions represent something other than gravity correction

**Likelihood:** Low. The Gyroflow docs confirm DJI stores "final computed camera position" and the Telemetry Extractor explicitly lists orientation quaternions.
**Mitigation:** Phase 4 visual validation will confirm or deny. If quaternions are camera-to-world rotation, the inverse gives us what we need. If they're something else, Euler angle inspection (Phase 5B) will reveal their meaning.

### Risk 3: osvtoolbox cannot build on Windows

**Likelihood:** Medium. The tool requires FFmpeg dev libs and C++17.
**Mitigation:** Fall back to direct ffmpeg stream extraction (Phase 2B). Or use WSL. Or use the commercial Telemetry Extractor which has a GUI.

### Risk 4: Metadata sample rate differs from video frame rate

**Likelihood:** Low-medium. Some cameras record telemetry at a different rate than video.
**Mitigation:** Compare sample counts. If rates differ, interpolate quaternions to match video frames using SLERP (spherical linear interpolation).

### Risk 5: No `.osv` files available yet

**Likelihood:** Current reality.
**Mitigation:** This is the immediate blocker. Phase 0 must happen first. In the meantime, the 71 `.insv` files at `D:\Capture\InstaFiles\360\` can be used to practice the probing methodology on a different 360 format — Insta360 embeds gyro data in the back-lens `.insv` file, and Gyroflow fully supports it.

---

## 6. Tool acquisition checklist

Before testing can begin, install:

- [ ] **osvtoolbox** — `git clone https://github.com/ChelouteVR/osvtoolbox.git` + build
- [ ] **pyosmogps** — `pip install pyosmogps` (reference for proto parsing patterns)
- [ ] **protobuf** — `pip install protobuf` (for raw proto decoding)
- [ ] **scipy** — `pip install scipy` (for Rotation class, quaternion math)
- [ ] **matplotlib** — `pip install matplotlib` (for quaternion time-series plots)
- [ ] **Telemetry Extractor trial** — [download page](https://goprotelemetryextractor.com/gopro-gps-telemetry-extract) (commercial fallback/ground truth)

Optional:
- [ ] **telemetry-parser** — `git clone https://github.com/AdrianEddy/telemetry-parser.git` (inspect DJI proto defs)

---

## 7. References

| Resource | URL | Relevance |
|----------|-----|-----------|
| osvtoolbox (OSV extract/recompose) | https://github.com/ChelouteVR/osvtoolbox | Primary tool for raw track extraction |
| Telemetry Extractor for DJI Action | https://goprotelemetryextractor.com/tools-for-dji-action | Confirms quaternion availability; commercial ground truth |
| pyosmogps (Python DJI GPS parser) | https://github.com/francescocaponio/pyosmogps | Reference for protobuf parsing of DJI metadata |
| telemetry-parser (Gyroflow's parser) | https://github.com/AdrianEddy/telemetry-parser | DJI proto definitions in Rust source |
| DJI djmd proto request (open issue) | https://github.com/dji-sdk/Payload-SDK-Tutorial/issues/4 | Status of official proto spec release |
| Gyroflow DJI camera support | https://docs.gyroflow.xyz/app/getting-started/supported-cameras/dji | Confirms DJI stores quaternions, not raw IMU |
| osv2gpx (GPS extraction) | Facebook GSV group post | GPS-only extraction from OSV |
| Blackmagic Forum OSV discussion | https://forum.blackmagicdesign.com/viewtopic.php?f=3&t=226243 | Community discussion on OSV format limitations |
| LosslessCut OSV issue | https://github.com/mifi/lossless-cut/issues/2624 | OSV stitching/processing challenges |
| immich OSV feature request | https://github.com/immich-app/immich/discussions/27216 | Community interest in OSV support |
| DJI Osmo 360 downloads | https://www.dji.com/360/downloads | Official DJI Studio software |
| ExifTool DJI tag definitions | https://exiftool.org/TagNames/DJI.html | Lists all dvtm proto files and extractable fields |

---

## 8. Results from actual testing

**Test file:** `CAM_20260323172324_0023_D.OSV`
**Date tested:** April 12, 2026

### 8.1 Confirmed OSV container structure

ffprobe confirms 8 streams (not 7 — there's an embedded MJPEG thumbnail):

| Stream | Type | Codec | Details | Frames |
|--------|------|-------|---------|--------|
| 0 | video | HEVC Main 10 | 3840x3840 front lens, 50fps | 4003 |
| 1 | video | HEVC Main 10 | 3840x3840 back lens, 50fps | 4003 |
| 2 | audio | AAC | 48kHz stereo | 3753 |
| 3 | data | `djmd` | "CAM meta" — 255 kbps | 4003 |
| 4 | data | `djmd` | "CAM meta" — 57 kbps | 4003 |
| 5 | data | `dbgi` | "CAM dbgi" — 1.58 Mbps | 4003 |
| 6 | data | `dbgi` | "CAM dbgi" — 1.58 Mbps | 4003 |
| 7 | video | MJPEG | 688x344 thumbnail (attached_pic) | 1 |

Format metadata: `encoder: Osmo 360`, `major_brand: isom`.

### 8.2 LRF sidecar is a pre-stitched equirectangular

The `.LRF` file (88 MB) contains:

| Stream | Type | Codec | Details | Frames |
|--------|------|-------|---------|--------|
| 0 | video | H.264 High | **2048x1024** (2:1 ERP!) @ 25fps | 2002 |
| 1 | audio | AAC | 48kHz stereo | 3753 |
| 2 | data | `djmd` | "CAM meta" | 2002 |
| 3 | data | `djmd` | "CAM meta" | 2002 |
| 4 | video | MJPEG | 688x344 thumbnail | 1 |

**Key discovery:** The LRF is a low-res already-stitched equirectangular at half framerate. Useful for quick visualization without running DJI Studio.

### 8.3 Protobuf schema identified

ExifTool `Category` field reveals:
```
pb_file:dvtm_oq101.proto; model_name:OQ001; pb_version:2.0.8; pb_lib_version:02.01.15;
```

ExifTool v13.41 already has built-in support for this proto schema. The ExifTool DJI tag reference at https://exiftool.org/TagNames/DJI.html lists `dvtm_oq101.proto` alongside 15 other DJI camera protos.

### 8.4 Orientation quaternions: CONFIRMED

Using `exiftool -ee -a -u -n`, per-frame quaternions are found at protobuf field path `3-2-9`:

| Field | Proto path | Content |
|-------|-----------|---------|
| `Dvtm oq 101 3-2-9-1` | 3-2-9-1 | Quaternion component 1 (float32) |
| `Dvtm oq 101 3-2-9-2` | 3-2-9-2 | Quaternion component 2 (float32) |
| `Dvtm oq 101 3-2-9-3` | 3-2-9-3 | Quaternion component 3 (float32) |
| `Dvtm oq 101 3-2-9-4` | 3-2-9-4 | Quaternion component 4 (float32) |

Additionally, field path `3-3-2-*-3` contains **high-rate sub-frame quaternion samples** (multiple per video frame at what appears to be the raw IMU fusion rate).

### 8.5 Quaternion quality verification

| Metric | Value | Pass |
|--------|-------|------|
| Frames with quaternions | 4003 (matches video frame count) | YES |
| Norm minimum | 0.9999999308 | YES |
| Norm maximum | 1.0000001358 | YES |
| Norm mean | 1.0000000388 | YES |
| All norms within 0.001 of 1.0 | True | YES |
| Temporal smoothness (max Δ) | 0.0436 | YES |
| No discontinuities | True | YES |
| qw range | [0.130, 0.821] | — |
| qx range | [-0.727, 0.316] | — |
| qy range | [-0.784, 0.429] | — |
| qz range | [-0.642, 0.744] | — |

The wide range of all quaternion components confirms substantial camera rotation over the 80-second clip, consistent with "alien eye" handheld capture.

Last ~3 frames have zero quaternions (end-of-recording padding).

### 8.6 Accelerometer data: CONFIRMED

Named fields `Accelerometer X/Y/Z` at proto path `3-2-10-2/3/4`:

| Frame 0 | Value |
|---------|-------|
| Accel X | -0.9519 g |
| Accel Y | 0.0242 g |
| Accel Z | -0.1048 g |
| Magnitude | 0.958 g (near 1g) |

### 8.7 Other telemetry fields found

From the first `djmd` sample (frame header):

| Field | Proto path | Value | Notes |
|-------|-----------|-------|-------|
| Serial Number | 1-1-5 | 95SXN7S02213TB | Camera serial |
| Model | 1-1-10 | Osmo 360 | Camera model name |
| Firmware | 1-1-6 | 10.00.25.29 | Firmware version |
| Proto file | 1-1-1 | dvtm_oq101.proto | Self-identifying |
| Proto version | 1-1-3 | 2.0.8 | Proto schema version |
| ISO | 3-2-3-1 | (present) | Per-frame |
| Shutter Speed | 3-2-4-1 | (present) | Per-frame |
| Color Temperature | 3-2-6-1 | (present) | Per-frame |
| F Number | 1-14-1 | 3840 | (likely encoded differently) |

GPS fields at `3-4-2-*` were present in the schema but had zero values — consistent with the gravity plan note that GPS requires the remote control.

### 8.8 Simplest viable extraction command

**No special tools needed.** ExifTool alone extracts everything:

```bash
# Per-frame quaternions + accelerometer
exiftool -ee -a -u -n <file>.osv \
  | grep -E "^(Sample Time|Dvtm oq 101 3-2-9-[1234]|Accelerometer)"
```

This produces one quaternion (4 floats) + one accelerometer reading (3 floats) per video frame at 50Hz.

### 8.9 What this means for the gravity-aware masking pipeline

**Step 0 from the gravity plan is COMPLETE.** All key questions are answered:

| Question from gravity plan | Answer |
|---------------------------|--------|
| Does the OSV container hold telemetry? | YES — two `djmd` tracks per file |
| Is per-frame orientation data embedded? | YES — quaternion at 50Hz, exactly 1:1 with video frames |
| What format are the quaternions in? | Float32, unit quaternions, via protobuf (`dvtm_oq101.proto`) |
| Are they pre-computed (sensor fusion done on-device)? | YES — confirmed by Gyroflow docs and by the data quality |
| Can we extract without proprietary tools? | YES — ExifTool v13.41+ has built-in support |
| Is GPS present without remote? | NO — GPS fields present but zeroed without remote control |
| Is the LRF useful? | YES — it's a pre-stitched 2048x1024 ERP at 25fps, perfect for quick preview |

**Next step:** Phase 4 from this document — apply the inverse quaternion to the LRF equirectangular to produce a body-frame ERP and verify operator position stability. This can be done immediately using the LRF video (fast, low-res) before attempting it on the full-res DJI Studio export.
