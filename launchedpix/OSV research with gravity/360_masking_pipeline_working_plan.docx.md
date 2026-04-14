**360° Operator Masking Pipeline**

Working Plan for Gravity-Aware Masking in 3DGS Reconstruction

Carryover document from Claude session  —  April 2026

# **1\. Problem statement and context**

When a 360° camera captures a scene, the camera operator is always visible in the footage. For 3D Gaussian Splatting (3DGS) reconstruction, the operator creates photometric inconsistencies that degrade both camera calibration (COLMAP) and reconstruction quality. The operator must be detected and masked out before reconstruction.

The FullCircle paper (Foroutan et al., 2026, arXiv:2603.22572) demonstrates a working solution for this problem using synthetic fisheye re-centering and SAMv2 segmentation. This working plan adapts and extends those ideas for our pipeline, with specific attention to the DJI Osmo 360 and the practical realities of casual handheld capture.

## **1.1 The gravity correction problem**

Consumer 360° cameras (DJI Osmo 360, Insta360 X-series) apply IMU-based gravity alignment during the stitching process. This rotation levels the horizon in the output equirectangular projection (ERP), which is desirable for viewing but destructive for masking.

**Why it matters:**

* In the camera’s native body-frame coordinates, the operator occupies a roughly fixed direction relative to the lenses (e.g. straight down a selfie stick).

* Gravity correction rotates the entire sphere per-frame based on camera tilt, which moves the operator’s apparent position in the ERP unpredictably.

* This makes the operator a moving target in ERP space even though they are physically stationary relative to the camera body.

* Disabling RockSteady (aggressive stabilization) is necessary but NOT sufficient. The more fundamental gravity alignment still occurs during stitching.

## **1.2 The two layers of rotation**

| Layer | What it does | Where it happens | Can you disable it? |
| :---- | :---- | :---- | :---- |
| RockSteady / Horizon Lock | Smooths motion, locks horizon across frames | In-camera or DJI Studio export | Yes. Disable before capture or export. |
| Gravity alignment (stitching) | Rotates sphere so IMU "down" \= ERP nadir, per-frame | DJI Studio stitching pipeline | Unknown. May require raw dual-fisheye data or reversing the rotation using extracted quaternions. |

## **1.3 The capture style variable**

The effectiveness of gravity-correction removal depends on how the camera is used during capture. This is a continuum:

| Capture style | Operator consistency (body-frame) | Masking difficulty |
| :---- | :---- | :---- |
| Camera on rigid pole, operator walks | Very high. Operator at fixed nadir. | Low. One direction works for all frames. |
| Handheld selfie stick, normal walking | High. Operator clusters near nadir with some drift. | Low-medium. Narrow search zone. |
| "Alien eye" (waving, poking into corners, overhead, angled under objects) | Moderate. Operator direction varies as stick angle changes. | Medium. Body-frame still better than world-frame, but per-frame refinement needed. |

Our primary capture style is "alien eye" exploration. Removing gravity correction will reduce variance in the operator’s position but will not make it fixed. We still need per-frame detection, but from a much better starting point.

# **2\. Prior art: FullCircle’s approach**

FullCircle (theialab/fullcircle on GitHub, forked from nv-tlabs/3dgrut) solves operator masking with a three-stage pipeline. Understanding this is the foundation for our work.

## **2.1 Stage 1: Coarse detection**

* Split raw dual-fisheye images into overlapping patches.

* Run YOLOv8 person detection on each patch.

* Run SAMv2 to refine detected person regions into masks.

* Masks are rough (distortion, partial crops) but provide the average pixel direction of the operator on the sphere.

* Output: a single direction vector (approximate center of the operator in spherical coordinates).

## **2.2 Stage 2: Synthetic fisheye generation**

* Stitch dual-fisheye into an omnidirectional (equirectangular) image.

* Rotate the sphere so the operator’s estimated direction becomes the center.

* Render a new synthetic 180° fisheye view from this re-centered sphere.

* The operator now appears at the center of the synthetic fisheye, in the low-distortion zone.

* Key insight: fisheye lenses distort heavily at edges but minimally at center. By re-centering on the operator, segmentation models see a clean, undistorted silhouette.

## **2.3 Stage 3: Clean segmentation and map-back**

* Prompt SAMv2 with the center pixel of the synthetic fisheye as a positive point prompt. No manual annotation needed.

* SAMv2 segments the operator cleanly in the re-centered view.

* Propagate masks temporally across frames (SAMv2’s video tracking). Works well because operator stays centered.

* Map final masks back through the inverse reprojection to the original dual-fisheye coordinate space.

* Use masks for both COLMAP calibration (exclude operator features) and 3DGS training supervision.

## **2.4 Key takeaway for our work**

FullCircle works with raw dual-fisheye images, avoiding the gravity correction problem entirely. Our pipeline processes DJI Osmo 360 footage through DJI Studio, which applies gravity correction during stitching. We need to either avoid this correction or undo it.

# **3\. Proposed approach**

## **3.1 Core idea (from collaborator)**

"If the direction the camera operator is known, then cube face images (or perspective crops) could be generated in that direction. Avoiding the gravity direction enforced by the manufactured stitching could help keep the orientation of the operator more consistent."

This decomposes into two actionable ideas:

1. Generate perspective (or cubemap) crops aimed at the operator’s estimated direction for segmentation. This is equivalent to FullCircle’s synthetic fisheye but using rectilinear crops instead.

2. Work in camera-body coordinates rather than gravity-corrected world coordinates, so the operator’s direction is more predictable across frames.

## **3.2 Pipeline overview**

The proposed pipeline has five stages:

### **Stage A: Extract per-frame orientation from OSV files**

* DJI Osmo 360 records panoramic video as .osv files (MP4-like containers with dual-fisheye streams and metadata).

* DJI cameras embed pre-computed orientation quaternions (sensor fusion done on-device), not raw gyro/accelerometer data.

* Extract these quaternions per-frame. This gives us the rotation the stitcher applied to level the horizon.

* Tool chain: ffprobe to identify metadata tracks, then a Python script using struct/binary parsing or Gyroflow’s telemetry parser.

### **Stage B: Stitch to ERP with known gravity correction**

Two sub-options:

1. Stitch normally via DJI Studio (with RockSteady off), then apply the inverse quaternion rotation per-frame in Python to produce a body-frame ERP. This is the practical path.

2. If DJI Studio allows exporting without gravity correction, use that directly. Needs testing.

### **Stage C: Estimate operator direction in body-frame**

* For rigid-pole captures: define once as nadir. Done.

* For alien-eye captures: run lightweight detection (YOLOv8 on a single perspective crop aimed at the expected zone) to refine per-frame. The body-frame ERP constrains the search to a much smaller region than the world-frame ERP.

* The ERP Perspective Planner tool can be adapted to visualize and define the expected operator zone.

### **Stage D: Generate perspective crops and segment**

* Render a perspective (pinhole) or fisheye crop from the body-frame ERP, aimed at the estimated operator direction.

* Operator appears centered and minimally distorted.

* Segment using SAMv2 with center-point prompt, exactly as FullCircle does.

* Propagate masks temporally.

### **Stage E: Map masks back to gravity-corrected ERP**

* Apply the forward quaternion rotation to map masks from body-frame ERP back to the gravity-corrected ERP.

* Masks are now aligned with the output that COLMAP and the 3DGS trainer expect.

* Optionally dilate masks slightly to account for segmentation boundary uncertainty.

# **4\. Immediate next steps**

## **4.1 Step 0: Probe OSV file structure**

Before building anything, determine what data is inside the .osv files.

### **Commands to run**

ffprobe \-v quiet \-print\_format json \-show\_format \-show\_streams \<file\>.osv

Reveals video streams (expect two for dual-fisheye), audio, and metadata/data streams with telemetry.

exiftool \-a \-u \-g1 \<file\>.osv

Dumps all metadata tags including proprietary DJI fields. Look for orientation, quaternion, gyro, accelerometer, or IMU tags.

ffprobe \-v quiet \-show\_entries stream=codec\_type,codec\_tag\_string,width,height \<file\>.osv

Identifies all stream types. Telemetry is often a "data" stream with a specific codec tag.

python \-c "import struct; f=open('\<file\>.osv','rb'); print(f.read(32).hex())"

Quick check of file magic bytes to confirm container format.

### **What to look for**

* A data/subtitle stream containing binary telemetry (quaternions, timestamps).

* XMP or EXIF fields with orientation data.

* Multiple video tracks (dual-fisheye \= two separate H.265 streams, or one side-by-side stream).

* Any reference to "gyro," "imu," "orientation," "quaternion," "attitude," or "stabilization" in stream metadata.

* The .lrf sidecar file that appears alongside .osv files. This may contain telemetry or low-res preview data.

## **4.2 Step 1: Extract a single frame and quaternion**

Once the telemetry location is identified:

1. Extract one video frame as an image (ffmpeg \-i file.osv \-vframes 1 frame.png).

2. Extract the corresponding quaternion from the telemetry stream.

3. Visualize: render the frame in the ERP Perspective Planner, apply the inverse quaternion, and verify the operator position shifts to a more predictable location.

## **4.3 Step 2: Validate with a controlled test**

* Take a short clip (10-20 seconds) with the Osmo 360 on a selfie stick, walking in a straight line.

* Export via DJI Studio with RockSteady off.

* Also extract the raw dual-fisheye frames from the .osv file.

* Compare operator position in gravity-corrected ERP vs. body-frame ERP (quaternion-reversed).

* The operator should cluster much more tightly in the body-frame version.

## **4.4 Step 3: Prototype masking crop**

1. From the body-frame ERP, render a perspective crop aimed at the estimated operator direction.

2. Run SAMv2 or YOLOv8 on the crop.

3. Map the mask back to the gravity-corrected ERP.

4. Validate against manual mask or visual inspection.

# **5\. Tools and resources**

## **5.1 Existing tools in our stack**

| Tool | Role in this pipeline |
| :---- | :---- |
| ERP Perspective Planner (v3) | Visualize and define perspective crop presets from ERP images. Adapt for body-frame operator masking viewpoints. |
| COLMAP | Camera calibration. Masks should exclude operator features. |
| Lichtfeld Studio | ERP-to-pinhole reframing. Relevant for perspective crop generation. |
| SAMv2 | Segmentation model. Center-point prompt on operator-centered crops. |
| YOLOv8 | Person detection for coarse operator localization. |
| Gyroflow (reference) | Open-source DJI telemetry parsers (Rust). Most relevant reference for quaternion extraction. |
| ffprobe / exiftool | Initial probing of OSV file structure and metadata. |

## **5.2 Key references**

| Reference | URL / identifier |
| :---- | :---- |
| FullCircle paper | arXiv:2603.22572 |
| FullCircle code | github.com/theialab/fullcircle |
| 3DGRT (base of FullCircle) | github.com/nv-tlabs/3dgrut |
| Gyroflow (telemetry parsers) | github.com/gyroflow/gyroflow |
| Gyroflow protobuf spec | docs.gyroflow.xyz/app/technical-details/gyroflow-protobuf |
| Gyroflow DJI camera support | docs.gyroflow.xyz/app/getting-started/supported-cameras/dji |
| Insta360 developer resources | onlinemanual.insta360.com/developer/en-us/resource/integration |
| DJI Osmo 360 support/FAQ | dji.com/support/product/360 |

## **5.3 Hardware context**

| Component | Spec |
| :---- | :---- |
| Camera | DJI Osmo 360 (dual 1"-type sensors, 8K panoramic, OSV format) |
| Workstation GPU | NVIDIA RTX 3090 Ti (24GB VRAM) |
| Capture method | Handheld selfie stick, exploratory "alien eye" style |
| Reconstruction target | 3D Gaussian Splatting via COLMAP calibration |

# **6\. Open questions**

## **6.1 File format questions (answered by Step 0\)**

* Does the .osv container hold two separate video streams (one per fisheye) or a single side-by-side stream?

* Is per-frame orientation data embedded as a metadata/data stream, or only in file-level EXIF?

* What format are the quaternions in? (WXYZ vs. XYZW, float32 vs. float64, frequency relative to video framerate.)

* Does DJI Studio read additional sidecar files (.lrf appears alongside .osv) that contain telemetry?

* Can DJI Studio export ERP without gravity correction? Is there an SDK or CLI option?

## **6.2 Pipeline design questions**

* Is perspective (rectilinear) or fisheye better for the masking crop? FullCircle uses synthetic fisheye (wider FOV captures the full operator even if direction estimate is slightly off). Rectilinear has less distortion but narrower FOV.

* What FOV should the masking crop use? Wider \= more forgiving of direction error. Narrower \= cleaner segmentation.

* Should the body-frame ERP be generated as an intermediate file on disk, or computed on-the-fly per masking crop?

* How does DJI’s invisible selfie stick algorithm (stick erasure in the stitch overlap zone) interact with operator masking? The stick is removed, but operator hands/arms near it may be partially erased or distorted.

## **6.3 Collaboration questions**

* "Cube face images" in collaborator’s vocabulary \= rectilinear perspective crops with \~90° FOV. This is one option among many (arbitrary-FOV pinhole crops, synthetic fisheye, etc.).

* Does the collaborator work with a different 360° camera (e.g. Insta360)? File format and telemetry differ, but geometric principles are identical.

* Should this pipeline target a single camera model or be camera-agnostic from the start?

# **7\. Glossary of terms**

Shared vocabulary for collaborator discussions.

| Term | Definition |
| :---- | :---- |
| ERP | Equirectangular projection. A 2:1 image mapping the full sphere onto a flat rectangle. Standard output of 360° stitching software. |
| Dual-fisheye | Raw output of consumer 360° cameras: two 180°+ fisheye hemisphere images from two back-to-back lenses. |
| Body-frame | Coordinate system fixed to the camera body. "Down" is the camera’s physical bottom, regardless of tilt. Operator direction is more stable here. |
| World-frame | Coordinate system where "down" is true gravity (from IMU). Gravity-corrected ERP is in world-frame. |
| Gravity correction | Per-frame rotation during stitching that aligns ERP so gravity points to nadir. Uses IMU data. |
| Quaternion | 4-component rotation representation (w, x, y, z). DJI cameras embed per-frame quaternions. Inverse quaternion undoes the rotation. |
| Nadir | Bottom of the sphere (directly below camera). In gravity-corrected ERP: center of bottom edge. In body-frame: physical bottom of camera. |
| Synthetic fisheye/perspective crop | Virtual camera view rendered from an ERP. Can be aimed at any direction on the sphere for clean, undistorted views. |
| SAMv2 | Segment Anything Model v2 (Meta). Foundation model for image/video segmentation. Accepts point prompts. |
| RockSteady | DJI’s aggressive electronic stabilization. Smooths motion across frames. Disable for photogrammetry. |
| OSV | DJI Osmo 360 panoramic video format. MP4-like container with dual-fisheye streams and telemetry metadata. |
| Cube face / cubemap | Alternative 360° representation: six square perspective views. "Cube face images" \= perspective crops at specific directions. |
| 3DGS | 3D Gaussian Splatting. Reconstruction technique using 3D Gaussian primitives. Requires multi-view images with known poses. |
| COLMAP | SfM/MVS pipeline for camera pose estimation. Operator features in images can corrupt pose estimation. |

# **8\. Conversation context for carryover**

This document was generated from a Claude session on April 7, 2026\. The session covered:

* Analysis of the FullCircle repo (theialab/fullcircle) and paper (arXiv:2603.22572), specifically the synthetic camera masking pipeline.

* Interpretation of a collaborator’s message proposing gravity-correction-aware masking using cube face crops aimed at the operator’s direction.

* Identification of two distinct layers of rotation (RockSteady vs. gravity alignment during stitching) and why disabling RockSteady alone is insufficient.

* Discussion of how "alien eye" capture style (waving camera on selfie stick into nooks/corners) affects operator position consistency in body-frame vs. world-frame coordinates.

* Research into DJI Osmo 360 file formats (.osv), embedded telemetry (DJI uses pre-computed quaternions, not raw gyro), and Gyroflow as a reference for telemetry extraction.

* The distinction between Insta360 .insv format (gyro data in back-lens file) and DJI .osv format (newer, less documented).

* Practical plan for probing OSV files with ffprobe and exiftool before writing extraction code.

**The key unresolved item from this session is the actual contents of the .osv file. Everything downstream depends on what telemetry is available and in what format. Start with Step 0\.**