# camera-geometry-lab

A Python toolkit for understanding what your camera actually captures — and using that knowledge to solve real problems in 3D reconstruction.

## What this project is about

Every camera turns 3D reality into a flat image differently. A fisheye lens crams a huge field of view into a circle. A rectilinear lens keeps straight lines straight but can only see a narrow cone. A 360 camera stitches two fisheye hemispheres into a full sphere.

These differences matter when you want to do photogrammetry or Gaussian Splatting, because the reconstruction pipeline needs to know exactly which direction each pixel is looking and how much of the world it covers.

This project builds tools to answer those questions for any calibrated camera, and then uses those answers to solve a specific practical problem: **removing the camera operator from 360 video before 3D reconstruction.**

## How it works (the short version)

The core engine takes a calibrated camera image and reprojects it onto a sphere (equirectangular projection — the same format as a 360 photo). For every pixel in the output, it computes:

- **Color** — sampled from the input image
- **Ray direction** — which way this pixel points in 3D, stored as a quaternion
- **Solid angle** — how much of the world this pixel covers (in steradians)

Solid angle is the key concept. A wide-angle fisheye pixel near the edge of the frame "sees" a huge patch of sky. A telephoto pixel sees a tiny sliver. Solid angle quantifies this regardless of which camera or lens produced the image. It's a universal resolution metric: if you know the solid angle per pixel, you know the actual sampling density at every point on the sphere.

The distortion math follows Agisoft Metashape's conventions (Appendix D) because that's where the calibration parameters come from.

## The 360 masking problem

When you walk around with a 360 camera on a selfie stick, you're always in the shot. For 3D Gaussian Splatting, that's poison — COLMAP sees you as a static object and tries to reconstruct you into the scene. You need to be detected and masked out before reconstruction.

The complication: consumer 360 cameras (DJI Osmo 360, Insta360) apply gravity correction during stitching. Each frame is rotated so "down" is always true gravity-down. This is great for viewing, but it makes the operator wander unpredictably across the equirectangular image — even though physically, you're always below the camera on the stick.

The solution is to undo the gravity correction using the camera's own IMU data, work in body-frame coordinates (where the operator stays roughly in one place), do the masking there, and then map the masks back.

## Project status

### Reprojection engine

- [x] Reproject pinhole (rectilinear) images to equirectangular
- [x] Reproject equidistant fisheye images to equirectangular
- [x] Reproject equisolid fisheye images to equirectangular
- [x] Compute equirectangular solid angle per pixel
- [x] Compute input-camera solid angle and remap to output space
- [x] Store ray directions as quaternions per pixel
- [x] Write color/mask PNGs + headerless float32 RAW geometry
- [x] CLI entry point with JSON config files
- [x] Refactor prototype into modular package (`src/camera_geometry_lab/`)
- [x] Baseline tests (solid angle sum, antipodal quaternion, config loading)
- [ ] Fix pinhole halo/double-image artifact (noted in original prototype)
- [ ] Upgrade from nearest-neighbor to bilinear resampling
- [ ] Add pose/extrinsics support (camera rotation before projection)
- [ ] Structured output metadata (JSON alongside RAW files)

### OSV telemetry extraction (DJI Osmo 360)

- [x] Probe OSV container structure (ffprobe: 2x HEVC 3840x3840, 2x djmd, 2x dbgi, audio, thumbnail)
- [x] Identify protobuf schema (`dvtm_oq101.proto`, built into ExifTool v13.41)
- [x] Extract per-frame orientation quaternions (field `3-2-9`, 50Hz, 1:1 with video)
- [x] Validate quaternion quality (unit norm to 7 decimal places, smooth temporal evolution)
- [x] Confirm accelerometer data present (~1g magnitude)
- [x] Discover LRF sidecar = pre-stitched 2048x1024 equirectangular at 25fps
- [x] Confirm GPS requires remote control (fields present but zeroed without it)
- [x] Document simplest extraction: `exiftool -ee -a -u -n <file>.osv`
- [x] Preserve a shareable telemetry report bundle for review and regeneration
- [ ] Extract and test LRF equirectangular frames for quick preview workflow
- [ ] Validate quaternion semantics (apply inverse to LRF frame, check operator stabilizes at nadir)

### Gravity-aware masking pipeline

- [x] Document the gravity correction problem and why it breaks masking
- [x] Design the 5-stage pipeline (extract quaternions, undo gravity, estimate operator direction, segment, map back)
- [x] Research prior art (FullCircle paper, synthetic fisheye re-centering, SAMv2)
- [ ] **Stage A** — Extract per-frame quaternions from OSV *(proven, needs packaging)*
- [ ] **Stage B** — Apply inverse quaternion to produce body-frame ERP
- [ ] **Stage C** — Estimate operator direction in body-frame coordinates
- [ ] **Stage D** — Generate perspective crop aimed at operator, segment with SAMv2
- [ ] **Stage E** — Map masks back to gravity-corrected ERP for COLMAP/3DGS

### Cameras tested

- [x] 3DMakerPro Eagle Max (equidistant fisheye) — `configs/eagle.json`
- [x] Insta360 One R 1-inch (equidistant) — `configs/insta360_oner_1inch.json`
- [x] Nikon D800 + 20mm f/2.8 (pinhole) — `configs/nikon_d800_20mm.json`
- [x] DJI Osmo 360 (telemetry extraction only, not yet reprojection)
- [ ] Fuji X-Pro2 (available for testing)
- [ ] DJI Mavic Pro 3 (available for testing)

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
camera-geometry-lab reproject --help
```

The JSON files under `configs/` preserve calibration examples from the prototype archive. They still point at local sample data under `launchedpix/SampleImages/`, so a fresh clone should copy and edit them for a real dataset instead of expecting them to run unchanged.

## Repo layout

| Directory | What's in it |
|-----------|-------------|
| `src/camera_geometry_lab/` | The active package — reprojection, ray math, distortion, solid angle, CLI |
| `configs/` | JSON job configs for the sample datasets |
| `tests/` | Geometry and config baseline tests |
| `device_reports/` | Curated, shareable device test bundles (manifest, markdown summary, telemetry JSON) |
| `tools/` | Repo utilities for building local artifacts from tracked report bundles |
| `report_data/` | Ignored local scratch outputs from ad hoc telemetry analysis |
| `launchedpix/` (local archive) | Original prototype and sample archive retained locally during the bootstrap transition |

For the tracked device-report conventions used in this repo, see [device_reports/README.md](device_reports/README.md).

## Background

This project is a collaboration between an imaging science researcher (launchedpix) and a pipeline/tooling engineer. The imaging science and camera model math comes from the research side. The data pipeline, masking automation, and practical testing with real hardware comes from the engineering side.

The original prototype was written as an educational tool to explore how different camera projections map onto the sphere. The 360 masking work grew out of a practical need: cleaning up DJI Osmo 360 footage for 3D Gaussian Splatting reconstruction, where the camera operator must be removed from every frame.
