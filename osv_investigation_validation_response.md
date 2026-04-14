# Response Document: Validation of `osv_investigation.md`

Date: 2026-04-13

This document is a standalone assessment of the claims made in [`osv_investigation.md`](osv_investigation.md). It is not a revision of that file. Its purpose is to separate:

- claims that are directly supported by the available evidence,
- claims that are directionally right but overstated,
- claims that remain plausible but unproven, and
- claims that are contradicted by direct inspection.

It also expands the analysis where the local evidence supports stronger conclusions than the original investigation document made.

## Scope and evidence base

This response is based on four evidence classes:

1. Direct inspection of local capture files:
   - `D:\Capture\deskTest\CAM_20260323172324_0023_D.OSV`
   - `D:\Capture\deskTest\CAM_20260323172324_0023_D.LRF`
   - `D:\Capture\ashland\CAM_20251106130749_0001_D.OSV`
   - `D:\Capture\beachevening\CAM_20251024183857_0127_D.OSV`
2. Tracked repo artifacts:
   - [`device_reports/osmo-360/osv-telemetry-2026-04-12/OSV_Telemetry_Report.md`](device_reports/osmo-360/osv-telemetry-2026-04-12/OSV_Telemetry_Report.md)
   - [`device_reports/osmo-360/osv-telemetry-2026-04-12/telemetry_report.json`](device_reports/osmo-360/osv-telemetry-2026-04-12/telemetry_report.json)
   - [`report_data/osv_ffprobe.json`](report_data/osv_ffprobe.json)
   - [`report_data/lrf_ffprobe.json`](report_data/lrf_ffprobe.json)
   - [`report_data/osv_exiftool_metadata.txt`](report_data/osv_exiftool_metadata.txt)
   - [`report_data/lrf_exiftool_metadata.txt`](report_data/lrf_exiftool_metadata.txt)
   - [`report_data/osv_telemetry_raw.txt`](report_data/osv_telemetry_raw.txt)
3. The broader project docs:
   - [`README.md`](README.md)
   - [`360_masking_gravity_aware_plan.md`](360_masking_gravity_aware_plan.md)
4. External documentation used only to validate externally referenced claims:
   - ExifTool DJI tags: <https://exiftool.org/TagNames/DJI.html>
   - ExifTool tag names PDF snippet for `dvtm_oq101`: <https://exiftool.org/TagNames.pdf>
   - Gyroflow DJI docs: <https://docs.gyroflow.xyz/app/getting-started/supported-cameras/dji>
   - Gyroflow protobuf docs: <https://docs.gyroflow.xyz/app/technical-details/gyroflow-protobuf>

## Validation standard

This document uses the following labels:

| Status | Meaning |
|---|---|
| Validated | Reproduced directly from local files, or strongly corroborated by both local data and primary documentation. |
| Partially validated | Core observation holds, but at least one important detail or interpretation is too strong. |
| Plausible, not fully validated | Numerically or structurally plausible, but not decisively proven from the available evidence. |
| Invalidated | Contradicted by direct local inspection. |

## Executive summary

The overall investigation is strongest on the telemetry side and weakest on the video-geometry side.

What holds up well:

- The `.OSV` file is an MP4-family container with two HEVC lens streams, two `djmd` metadata tracks, two `dbgi` tracks, audio, thumbnail, and a trailing `camd` box.
- The per-frame quaternions at `3-2-9` are real, high quality, frame-aligned, and already sufficient for a first masking pipeline implementation.
- The high-rate `3-3-2` quaternion subgroup is real and significantly richer than the original tracked report bundle captured.
- The `2-6` calibration payload is real, repeated as 8 front/back pairs, and is stable across captures and firmware versions.
- The `dbgi` tracks really do carry a separate debug protobuf and clearly expose the `OV68A40` sensor identifier.

What does not hold up:

- The `.LRF` is not a stitched equirectangular preview. A fresh extracted frame is visibly a side-by-side dual-fisheye preview.
- Because of that, the body-frame validation section in `osv_investigation.md` is not reliable as written.
- The temporary script cited by the investigation is internally inconsistent about rotation direction and image model, which further weakens the body-frame result.

The most important practical conclusion is this:

- The telemetry work is strong enough to proceed.
- The LRF can still be useful as a small companion file and as a reduced-rate telemetry source.
- But it should not currently be treated as a trusted stitched ERP input for body-frame masking validation.

## High-level verdict matrix

| Topic | Verdict | Notes |
|---|---|---|
| OSV container structure | Validated | Reproduced with `ffprobe` from the actual file. |
| LRF file exists and is smaller / half-rate | Validated | Reproduced with `ffprobe`. |
| LRF is a stitched ERP | Invalidated | Fresh frame extraction shows dual-fisheye preview, not ERP. |
| ExifTool support for `dvtm_oq101.proto` | Validated | Matches local behavior and ExifTool docs. |
| Per-frame quaternion path `3-2-9` | Validated | Reproduced directly; tracked bundle stats match. |
| Per-frame accelerometer path `3-2-10-{2,3,4}` | Validated | Reproduced directly; ExifTool docs match. |
| High-rate quaternion path `3-3-2` | Validated | Reproduced directly from the live OSV. |
| `camd` as embedded MP4 with only 2 `djmd` tracks | Validated | Verified by raw byte inspection and extracted payload probe. |
| Secondary `djmd` is lightweight exposure-like metadata | Partially validated | Core claim holds, but packet-size claim is overstated. |
| Factory calibration in `2-6` | Validated | Reproduced directly and cross-file stable. |
| Brown-Conrady / OpenCV interpretation of `2-6-*-1..8` | Plausible, not fully validated | Very plausible numerically, but not fully proven from local evidence alone. |
| `dbgi` sensor ID `OV68A40` | Validated | Found directly in raw `dbgi` bytes. |
| GPS fields present but zero without GPS source | Partially validated | ExifTool docs support field mapping; local outputs are consistent with absent/default-zero GPS. |
| "GPS requires remote control" | Plausible, not fully validated | Consistent with notes, not independently proven here. |
| LRF telemetry equals every other OSV quaternion | Partially validated | Spot-check of first 10 matching timestamps succeeded. |
| Body-frame validation using LRF ERP | Invalidated | The image-model assumption is wrong. |

## Detailed assessment

### 1. Container structure

This section of [`osv_investigation.md`](osv_investigation.md) is substantially correct.

Direct `ffprobe` on the real `deskTest` OSV reproduced:

| Stream | Type | Codec tag | Size / frames | Handler |
|---|---|---|---|---|
| 0 | video | `hvc1` | `3840x3840`, `4003` frames | `VideoHandler` |
| 1 | video | `hvc1` | `3840x3840`, `4003` frames | `VideoHandler` |
| 2 | audio | `mp4a` | `3753` frames | `SoundHandler` |
| 3 | data | `djmd` | `4003` packets | `CAM meta` |
| 4 | data | `djmd` | `4003` packets | `CAM meta` |
| 5 | data | `dbgi` | `4003` packets | `CAM dbgi` |
| 6 | data | `dbgi` | `4003` packets | `CAM dbgi` |
| 7 | video | MJPEG thumbnail | attached pic | none |

Format-level metadata also matches:

- encoder: `Osmo 360`
- compatible brands: `isom, iso2, mp41`
- ExifTool category: `pb_file:dvtm_oq101.proto;model_name:OQ001;pb_version:2.0.8;pb_lib_version:02.01.15;`

Verdict: `Validated`

### 2. LRF sidecar

The existence and broad structure of the LRF are real:

| Stream | Type | Codec tag | Size / frames |
|---|---|---|---|
| 0 | video | `avc1` | `2048x1024`, `2002` frames |
| 1 | audio | `mp4a` | `3753` frames |
| 2 | data | `djmd` | `2002` packets |
| 3 | data | `djmd` | `2002` packets |
| 4 | video | MJPEG thumbnail | attached pic |

So the LRF is definitely:

- smaller,
- half-rate relative to the OSV,
- still telemetry-bearing,
- missing the `dbgi` tracks present in the full OSV.

However, the most important interpretation in the investigation is wrong:

- A freshly extracted frame from the actual LRF is not a stitched ERP.
- It is a side-by-side dual-fisheye preview image.
- That means the claim in `osv_investigation.md` that the LRF is a "fully stitched low-res equirectangular" is incorrect.

The geometric consequence matters more than the naming error. ERP math and dual-fisheye preview math are not interchangeable.

Verdict: `Partially validated`, with the "stitched ERP" claim `Invalidated`

### 3. ExifTool support and protobuf schema identification

This section is well supported.

Local evidence:

- ExifTool successfully decodes the file without any custom proto compilation.
- The file self-identifies as `dvtm_oq101.proto`.

External confirmation:

- ExifTool's DJI tag documentation explicitly lists `dvtm_oq101.proto` under supported DJI protobuf protocols.
- ExifTool's DJI tag reference also explicitly maps:
  - `dvtm_oq101_3-2-3-1` -> `ISO`
  - `dvtm_oq101_3-2-4-1` -> `ShutterSpeed`
  - `dvtm_oq101_3-2-6-1` -> `ColorTemperature`
  - `dvtm_oq101_3-2-10-2/3/4` -> `AccelerometerX/Y/Z`
  - `dvtm_oq101_3-4-2-1` -> `GPSInfo`
  - `dvtm_oq101_3-4-2-2` -> `AbsoluteAltitude`
  - `dvtm_oq101_3-4-2-6-1` -> `GPSDateTime`

Verdict: `Validated`

### 4. Per-frame quaternions at `3-2-9`

This is one of the strongest parts of the original investigation.

The tracked report bundle and the live file agree on the main statistics:

- `4003` quaternion samples for `4003` video frames
- norm min `0.9999999308`
- norm max `1.0000001358`
- norm mean `1.0000000388`
- max frame-to-frame delta `0.04355`
- zero-quaternion frames `0`

This directly supports:

- the field-path identification,
- one quaternion per frame,
- high signal quality,
- frame-accurate orientation availability.

External Gyroflow documentation also supports the general interpretation that DJI stores quaternions representing the final fused camera orientation rather than raw gyro samples.

Verdict: `Validated`

### 5. High-rate quaternion sub-samples at `3-3-2`

This section goes beyond the older tracked report bundle, but it is reproducible from the live OSV.

Directly reproduced from the file:

- subgroup `3-3-2-1` appears once per frame with one sequence value per frame
- subgroup `3-3-2-1-2` count: `4003`
- sequence range: `41022` to `45024`
- subgroup `3-3-2-2-2` count: `1`
- subgroup `3-3-2-2` sequence: `41021`
- subgroup `3-3-2-1-3-1` sample count: `79616`
- subgroup `3-3-2-2-3-1` sample count: `20`
- effective subgroup-1 average: `79616 / 4003 = 19.889` samples per video frame
- subgroup `-4` value: constant `12.25` across both groups

This strongly supports the "main high-rate stream plus one short initialization/lookback stream" interpretation.

The specific claim that the frame quaternion is "byte-identical to sub-sample ~6" was not independently re-derived end-to-end in this response, but the raw excerpt shown during validation is consistent with that claim and does not conflict with the observed structure.

Verdict: `Validated`, with one sub-detail not fully re-proven

### 6. Secondary `djmd` track

The broad interpretation is good: the secondary metadata stream is much lighter and does not appear to carry the same rich motion metadata as the primary track.

Evidence:

- OSV stream 4 packet count: `4003`
- packet-size distribution:
  - `142` bytes: `3939` packets
  - `141` bytes: `63` packets
  - `310` bytes: `1` packet
- mean primary-track packet size is about `637.35` bytes
- raw demux of the secondary stream contains the string `Osmo OQ001` exactly `4003` times

This supports the claim that it is a lightweight per-frame record with a different role than the primary telemetry track.

What does not hold:

- It is not strictly "fixed 141 bytes per frame."
- The first packet is clearly larger, which is consistent with a header-bearing first record.
- Most packets are actually `142` bytes, not `141`.

Verdict: `Partially validated`

### 7. `camd` MP4 box

This finding is real and important.

The local file bytes at the claimed location show:

- `0x67aa086e`: box header beginning with `00 30 9a f1 63 61 6d 64`
- `0x67aa0876`: inner payload beginning with `00 00 00 1c 66 74 79 70`

That means:

- `0x67aa086e` is the `camd` box header,
- `0x67aa0876` is the start of the embedded MP4 payload inside the box.

Extracting that payload and probing it produces a valid MP4 with exactly:

- two `djmd` tracks,
- `4003` packets each,
- no video,
- no audio,
- no `dbgi`.

This is one of the strongest expanded findings in the investigation because it reveals a compact telemetry-only extraction path.

One related expansion beyond the original document:

- The LRF metadata also reports an embedded `camd` blob in [`report_data/lrf_exiftool_metadata.txt`](report_data/lrf_exiftool_metadata.txt), so both OSV and LRF may carry nested camera-data payloads.

Verdict: `Validated`

### 8. Factory calibration in `2-6`

This is another strong section.

Directly reproduced:

- active front lens block: `2-6-1`
- active back lens block: `2-6-2`
- additional blocks present: `11,12,13,14,15,16,17,18,19,20,21,22,23,24`

So the calibration structure is not a simple `1..16` run. It is `1,2,11..24`.

Observed properties that hold:

- the front/back active calibration values listed in the investigation match the actual file,
- the quaternion fields `2-6-*-28-{1..4}` are unit quaternions,
- the odd-numbered lens blocks share one set of `k1,k2,p1,p2`,
- the even-numbered lens blocks share a different set of `k1,k2,p1,p2`,
- `fx` drifts across blocks while distortion terms remain fixed within each lens family.

Cross-file comparison is especially convincing:

- hashing all extracted `2-6-*` lines from the Oct 2025, Nov 2025, and Mar 2026 files produced the same hash for all three captures.
- This strongly supports the claim that these calibration sets are device-burned or device-persistent rather than session-generated.

What is still interpretation rather than strict proof:

- labeling the additional sets as "temperature-dependent calibration" is plausible,
- but the available evidence only proves that multiple persistent calibration states exist and vary in focal center / focal length / extrinsic values.

Verdict: `Validated` for structure and persistence, `Plausible` for the temperature-history explanation

### 9. Brown-Conrady / OpenCV interpretation

The original document argues that `2-6-*-1..8` should be read as:

- `fx, fy, cx, cy, k1, k2, p1, p2`

This is very plausible:

- the magnitudes are numerically sensible,
- the first four values look exactly like focal lengths and principal points,
- the next four behave like residual distortion terms,
- the field grouping is stable across all calibration sets,
- and the overall structure is consistent with common camera-calibration representations.

However, this response did not independently validate the full chain of evidence behind the phrases "confirmed" and "documented in DJI's DewarpData XMP spec" from a DJI primary source.

So the right confidence level here is:

- very plausible engineering interpretation,
- not fully proven solely from the local evidence collected in this response.

The unknown arrays at `-22` and `-23` remain genuinely unresolved.

Verdict: `Plausible, not fully validated`

### 10. `dbgi` tracks and sensor identification

This section is well supported.

Directly reproduced:

- stream 5 packet count: `4003`
- stream 6 packet count: `4003`
- stream 5 mean packet size: `3949.85` bytes
- stream 6 mean packet size: `3949.18` bytes

Raw extraction of stream 5 contains the ASCII strings:

- `dbginfo_oq101.proto`
- `OV68A40`

That is enough to validate:

- there is a separate debug protobuf family,
- the sensor identifier really is present in the debug stream,
- the `OV68A40` identification is not just speculative.

Verdict: `Validated`

### 11. Cross-file comparison

The core cross-file conclusions are strong.

Directly reproduced across:

- `beachevening` Oct 2025
- `ashland` Nov 2025
- `deskTest` Mar 2026

Observed changes:

- proto lib version changes from `02.01.13` to `02.01.15`
- proto version changes from `2.0.7` to `2.0.8`
- firmware changes from `10.00.14.19` to `10.00.25.29`
- device/session ID changes between recordings

Observed stability:

- same calibration payload hash across all three files,
- same active front/back `fx` values across all three files.

The original conclusion that the calibration payload is stable across time and firmware is well supported.

Verdict: `Validated`

### 12. GPS fields

This section needs a more careful reading than the original investigation gave it.

What is solid:

- ExifTool's official tag docs explicitly map `dvtm_oq101_3-4-2-1` to `GPSInfo`, `3-4-2-2` to `AbsoluteAltitude`, and `3-4-2-6-1` to `GPSDateTime`.
- ExifTool also documents an important rule: missing numerical tags in protobuf output should be treated as default zero.

What local inspection showed:

- repeated `3-4-1-*` and `3-4-2-3` values are present in the deskTest OSV,
- the specific GPS coordinate/date subfields cited in the investigation do not print in the normal local ExifTool output,
- that absence is consistent with ExifTool's documented "missing numeric field implies default zero" behavior.

So the correct refined conclusion is:

- the GPS branch mapping is real,
- the local captures do appear consistent with "no usable GPS samples recorded,"
- but the exact reason for the missing data is not proven solely by this response.

The statement that GPS requires the dedicated remote may be true, but it was not independently demonstrated here.

Verdict: `Partially validated`

### 13. LRF telemetry versus OSV telemetry

This claim deserves to be separated into two parts:

#### 13.1 Telemetry equivalence

A direct spot-check of the first 10 matching timestamps succeeded:

- LRF timestamps `0.00, 0.04, ..., 0.36`
- matched OSV timestamps `0.00, 0.04, ..., 0.36`
- all first 10 quaternion components matched exactly at those sampled times

That strongly suggests the LRF carries a reduced-rate subset of the same orientation stream.

What this response did not do:

- re-run a full-file equivalence proof for every LRF frame.

Verdict: `Partially validated`, leaning strongly positive

#### 13.2 Video geometry

This is where the original investigation fails.

- The LRF video is not a stitched ERP.
- Therefore it cannot be used directly as if it were an ERP in a quaternion-undo script.

This distinction is crucial because it breaks the later body-frame validation claims.

Verdict: `Invalidated` for the ERP interpretation

### 14. Body-frame ERP validation

This is the most important invalidation in the document.

The original investigation says it "applied the inverse per-frame quaternion to LRF ERP frames." That does not survive inspection.

Three problems are present:

1. The LRF frames are not ERP frames.
2. The cited script at `D:\tmp\bodyframe_test\make_bodyframe_erp.py` assumes ERP input by construction.
3. The script is internally inconsistent about rotation direction:
   - it says it will use the inverse,
   - it computes `r_world_to_body = r_body_to_world.inv()`,
   - but the actual mapping call is `r_body_to_world.apply(flat_rays)`,
   - so the inverse object it computes is not the transform it actually applies.

This means the body-frame result images are not a valid confirmation of the quaternion semantics for ERP-space undoing.

The output imagery itself also looks like a severe warp of a dual-fisheye source rather than a sensible world-frame-to-body-frame ERP rotation.

So the correct conclusion is:

- the telemetry may still be correct,
- but this specific validation pipeline does not prove the body-frame claim.

Verdict: `Invalidated`

## Additional findings beyond the original investigation

### A. The `camd` offset should be read as two distinct numbers

The original investigation gives one offset. The direct byte inspection reveals two useful addresses:

- `0x67aa086e`: start of the `camd` box header
- `0x67aa0876`: start of the embedded MP4 payload inside the `camd` box

That distinction matters if a future extraction tool wants to copy only the inner MP4 payload rather than the enclosing box.

### B. The calibration block IDs are semantically sparse

The presence of `1,2,11..24` suggests these IDs are protocol-defined keys, not a simple zero-based or contiguous array. A future parser should preserve original IDs instead of normalizing them away too early.

### C. Naive ExifTool counting can be misleading because of nested payloads

The presence of `camd` inside both OSV and LRF means:

- some tags may appear once in a track and again in embedded camera data,
- some fields may be surfaced differently depending on ExifTool's embedded-data traversal behavior,
- packet-level validation with `ffprobe` or raw demux is safer when exact attribution to one stream matters.

### D. The repo was already warning that LRF validation was unfinished

[`README.md`](README.md) still lists these as incomplete:

- "Extract and test LRF equirectangular frames for quick preview workflow"
- "Validate quaternion semantics (apply inverse to LRF frame, check operator stabilizes at nadir)"

That caution turned out to be warranted.

## Implications for the masking pipeline

The outcome for project planning is not "the telemetry work failed." It is more nuanced:

### What is ready to build on

- per-frame quaternions,
- high-rate sub-samples if needed later,
- persistent per-device lens calibration,
- a compact telemetry-only extraction path via `camd`,
- `dbgi`-backed hardware identification.

### What is not yet proven

- a correct world-frame to body-frame validation path using the current LRF imagery,
- any conclusion that depends on the LRF being a true ERP,
- any seam-analysis conclusion built on those warped outputs.

### What this means practically

The safest next path is:

1. treat the telemetry extraction work as mature enough to package,
2. stop using the current LRF-as-ERP assumption,
3. validate quaternion semantics against a genuinely stitched ERP source,
4. only then resume operator-clustering and mask-backprojection experiments.

## Recommended next investigations

1. Determine what the LRF actually is geometrically.
   - It looks like a dual-fisheye preview frame packed into `2048x1024`, not a stitched ERP.
   - Confirm whether it is a simple rescaled preview of the two primary lens streams or a lightly processed stitch-preview format.

2. Build a trustworthy stitched validation path.
   - Use DJI Studio output, or stitch the dual fisheyes independently using the `2-6` calibration payload.
   - Then apply the quaternion undo in a true ERP domain.

3. Package the telemetry extractor before the masking pipeline.
   - The telemetry side is now much stronger than the image-domain validation side.

4. Formalize the `2-6` parser.
   - Persist all 16 observed calibration blocks with raw IDs.
   - Keep unresolved fields verbatim rather than discarding them.

5. Re-test LRF telemetry equivalence at full length.
   - The first 10 sampled matches are excellent evidence, but a whole-file parity check would close the loop cleanly.

6. Treat the GPS conclusion carefully.
   - It is fair to say "no usable GPS observed in these captures."
   - It is not yet fair to say this response proved the exact operational dependency chain that caused that absence.

## Final conclusion

`osv_investigation.md` is a valuable investigation document, and much of its telemetry reverse-engineering work is genuinely strong. The core OSV/container/quaternion/calibration findings are good and should be retained with high confidence.

But the document overstates confidence in the LRF image interpretation, and that error propagates into the body-frame validation section. The telemetry extraction work is ahead of the geometric validation work. The right next move is not to discard the investigation, but to split it mentally into:

- a mostly successful telemetry and calibration reverse-engineering effort, and
- an image-domain validation branch that needs to be re-done with a correct stitched input representation.
