# Step 4: Full COLMAP Dataset Rewrite Plan

## Goal

Take a COLMAP dataset exported from Metashape (with native fisheye/equidistant/equisolid camera models and distortion) and rewrite it so that:
- Every wide-FOV image is split into multiple pinhole (cubemap) sub-images
- Every sub-image has a correct, validated mask
- `cameras.txt` contains pinhole camera entries for each sub-image
- `images.txt` contains correct poses (position + rotation) for each sub-image
- The result can be fed directly to any GS training software that expects pinhole cameras

This is the end goal of the entire project.

---

## Inputs

### From Metashape (via COLMAP export)

```
colmap_export/
  cameras.txt     # Camera models (EQUISOLID_FISHEYE, EQUIDISTANT, PINHOLE, etc.)
  images.txt      # Per-image: quaternion rotation, translation, camera_id, image name
  points3D.txt    # Sparse 3D point cloud (optional, for validation)
  images/         # The actual image files
```

### From masking pipeline

```
masks/
  <image_name>_mask.png   # Combined lens boundary + operator mask per source image
```

---

## Outputs

```
colmap_pinhole/
  cameras.txt     # All PINHOLE entries (one per cubemap face type per original camera)
  images.txt      # 5x entries per original wide-FOV image, each with correct extrinsics
  points3D.txt    # Requires rewriting (see "Point Redistribution" section below)
  images/         # Cubemap face images
    frame_001_lens0_PZ.png
    frame_001_lens0_PX.png
    frame_001_lens0_NX.png
    frame_001_lens0_PY.png
    frame_001_lens0_NY.png
    ...
  masks/          # Corresponding masks
    frame_001_lens0_PZ_mask.png
    frame_001_lens0_PX_mask.png
    ...
```

---

## Components

### Component 1: COLMAP Parser

**What:** Read `cameras.txt` and `images.txt` into structured data.

**Status:** Partially exists.
- camera-geometry-lab: no COLMAP parser yet
- reconstruction-zone: `colmap_validation.py` has `parse_cameras_txt()`, `parse_images_txt()`, `parse_points3D_txt()` (source: reconstruction_gui/colmap_validation.py)
- Mike's reference: @gradeeterna's equirect-to-cubemap script (mentioned in docx, not yet obtained) likely has COLMAP I/O

**Needs:**
- Support for COLMAP's fisheye camera models (SIMPLE_RADIAL_FISHEYE, RADIAL_FISHEYE, OPENCV_FISHEYE, THIN_PRISM_FISHEYE)
- reconstruction-zone currently supports: SIMPLE_PINHOLE, PINHOLE, SIMPLE_RADIAL, RADIAL, OPENCV
- May need to handle Metashape's COLMAP export format specifically (which camera model IDs does Metashape use for equisolid?)

**Key question:** What camera model does Metashape write to cameras.txt for equisolid fisheye? This needs to be verified by exporting from Metashape and inspecting the file.

### Component 2: Cubemap Geometry Computation

**What:** For each cubemap face direction, compute the pinhole camera intrinsics and the rotation relative to the original camera.

**Owner:** This is imaging science / math territory (Mike's domain).

**The math:**

A cubemap face is a pinhole camera with:
- Image size: N x N (square)
- Focal length: f = N / 2 (90-degree FOV per face)
- cx, cy = 0, 0 (centered)
- No distortion (it's a perfect pinhole)

The 5 face directions (relative to the original camera's optical axis +Z):

| Face | Direction | Rotation from +Z |
|------|-----------|-----------------|
| +Z (front) | (0, 0, 1) | Identity |
| +X (right) | (1, 0, 0) | 90 degrees around Y |
| -X (left) | (-1, 0, 0) | -90 degrees around Y |
| +Y (up) | (0, 1, 0) | -90 degrees around X |
| -Y (down) | (0, -1, 0) | 90 degrees around X |

**Extrinsic computation for each cubemap face:**

Given the original camera's rotation R_orig (from images.txt, stored as quaternion + translation):
```
R_face = R_orig * R_cubemap_direction
t_face = t_orig  (translation doesn't change -- same camera center)
```

The key insight: all 5 cubemap faces share the same camera center (translation) as the original fisheye camera. Only the rotation changes.

**Face size determination:**

Mike's docx provides the formula for matching equirect resolution:
```
CentralPixel_SA = 4 * arctan(1 / (w * sqrt(w*w + 2)))
```
For 8K equirect (SA = 6.69e-7), this gives w = 2445. For the X5's native resolution, this should be computed from the solid angle at the center of the fisheye.

Practical defaults: 1920x1920 (common), 2048x2048 (power of 2), or computed per-camera.

### Component 3: Image Remapping (Fisheye -> Cubemap Face)

**What:** For each cubemap face pixel, find the corresponding source pixel in the fisheye image.

**Status:** Proof of concept exists (Mike's `equi_2_cubefaces.py`), but uses forward splatting. Needs inverse mapping.

**Inverse mapping approach (preferred):**

For each output pixel (u, v) in cubemap face N:
1. Compute the 3D ray direction: `ray = R_face_inverse * pinhole_to_ray(u, v, f_cube)`
2. Project that ray into the source fisheye using: `ray_to_equisolid(ray)` + `apply_distortion()` + pixel coords
3. Store as `map_x[v, u]`, `map_y[v, u]`
4. Apply with `cv2.remap(source_image, map_x, map_y, INTER_LINEAR)`
5. Apply same remap to mask with `INTER_NEAREST`

**Critical optimization:** The remap LUT depends only on the camera calibration and face direction, NOT on the image content. Compute once per (camera_id, face_direction) pair and reuse across all frames from that camera.

**Source for the math:**
- Ray-to-equisolid projection: `Reproject_FEES_IMM_2_Equirectangular.py`, `ray_to_projection()` line 138
- Forward distortion: same file, `distort_points()` line 118
- Pixel coordinate conversion: same file, lines 340-345

### Component 4: Mask Generation and Propagation

**What:** Ensure every cubemap face image has a correct mask.

**Owner:** Alex's domain.

**Pipeline:**

```
Source fisheye image
       |
       v
[Lens boundary mask]  <-- From calibration (Track 3 of this plan)
       |
       v
[Operator mask]  <-- From reconstruction-zone (SAM3/YOLO26)
       |
       v
[Combined mask = lens_boundary AND operator]
       |
       v
[Remap to each cubemap face using same LUT as image]
       |
       v
5 cubemap face masks
       |
       v
[Validation against COLMAP sparse reconstruction]
```

**Key decisions:**
- Mask before split or after split?
  - **Before** (recommended): Run segmentation once on the full fisheye image, then remap the mask to each face. Faster, more context for the segmentation model.
  - **After**: Run segmentation on each cubemap face independently. 5x the inference cost, but models work better on perspective images.
  - **Hybrid**: Lens boundary before split, operator after split (cubemap faces are perspective images, which SAM3/YOLO handle better).

- Mask format: Binary PNG, 0 = invalid, 255 = valid. One mask per cubemap face image. Same filename convention with `_mask` suffix.

### Component 5: COLMAP Writer

**What:** Write the new `cameras.txt` and `images.txt` with pinhole entries.

**cameras.txt format:**
```
# Camera list with one line of data per camera:
# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
# For PINHOLE: PARAMS = fx, fy, cx, cy

1 PINHOLE 1920 1920 960.0 960.0 960.0 960.0
```

One camera entry per unique (original_camera_id, face_size) combination. All faces of the same size share the same pinhole parameters (f = N/2, cx = cy = N/2).

Actually -- we might need one camera per face direction if the face sizes differ (e.g., if we clip the +Y/-Y faces differently). But for standard cubemap, all faces are identical, so one camera entry suffices.

**images.txt format:**
```
# IMAGE_ID QUAT_W QUAT_X QUAT_Y QUAT_Z TX TY TZ CAMERA_ID IMAGE_NAME
# (followed by a line of 2D point observations — see "Point Redistribution" below)

1 0.707 0.0 0.707 0.0  1.5 2.3 0.1  1  frame_001_lens0_PX.png
POINT2D_X1 POINT2D_Y1 POINT3D_ID1 POINT2D_X2 POINT2D_Y2 POINT3D_ID2 ...
```

Each original image produces 5 entries with:
- Same translation (TX, TY, TZ) as original
- Modified rotation: original quaternion composed with face direction quaternion
- Unique IMAGE_ID
- New IMAGE_NAME matching the cubemap face file
- Redistributed 2D point observations (see below)

### Component 6: Point Redistribution

**What:** Rewrite `points3D.txt` and the 2D observation lines in `images.txt` so that 3D-to-2D correspondences are correct for the cubemap face images.

**Why this can't be skipped for a COLMAP-consistent rewrite:** COLMAP's `points3D.txt` stores, for each 3D point, a list of (IMAGE_ID, POINT2D_IDX) pairs indicating which images observe it and where. The `images.txt` observation lines store the reverse mapping: for each image, the 2D positions and their corresponding POINT3D_IDs. After splitting one fisheye image into 5 cubemap faces, every 2D observation from the original image must be:

1. **Reprojected** into the new cubemap face coordinate system using the face's pinhole intrinsics and the composed extrinsic rotation
2. **Assigned to the correct face** — the face where the reprojected 2D point actually falls within bounds
3. **Updated** with the new pixel coordinates in the cubemap face image
4. **Removed** from faces where the point falls outside the image or inside a masked region

**points3D.txt must also be rewritten:** Each track entry references IMAGE_IDs. The original IMAGE_ID no longer exists — it's been replaced by 5 face IMAGE_IDs. The track must be updated to reference whichever face(s) the point is visible in.

**Implementation approach:**
- For each 3D point in points3D.txt, and for each of its original (IMAGE_ID, POINT2D_IDX) observation pairs:
  - Look up the original image's extrinsics and the 2D pixel position
  - Project the 3D point into each of the 5 cubemap face cameras (using the composed extrinsics)
  - The face where the projection falls within [0, N) x [0, N) and outside the mask is the correct assignment
  - Record the new (FACE_IMAGE_ID, new_pixel_x, new_pixel_y) observation
- Rewrite points3D.txt with updated track lists
- Rewrite images.txt observation lines with the reassigned 2D points

**Edge cases:**
- A point near a cubemap face boundary might project into two adjacent faces. Assign to the face where it's furthest from the edge (most robust for BA).
- A point that falls inside a masked region on all faces should be dropped from the track for that original image.
- If a 3D point loses all observations after redistribution, it should be removed from points3D.txt.

**Note on GS-only workflows:** Some GS trainers (e.g., gsplat, 3DGS) only need cameras.txt + images.txt + the images themselves, and use their own SfM or skip it entirely. For these, point redistribution can be deferred. But for a fully COLMAP-consistent export that supports incremental BA or further COLMAP processing, this component is required.

### Component 7: Validation

**What:** Verify the rewritten dataset is geometrically correct.

**Approaches:**

1. **Sparse point reprojection:**
   - Load `points3D.txt` (the 3D points from the original reconstruction)
   - For each point, project it into the new pinhole cubemap cameras
   - Verify it lands at a reasonable pixel location
   - Verify it falls inside the mask (not in a masked region)
   - Compare reprojection error against the original

2. **Visual inspection:**
   - Render each cubemap face with its mask overlay
   - Check: do adjacent faces show consistent content at shared edges?
   - Check: does the mask correctly exclude the operator/equipment?

3. **GS training test:**
   - Feed the rewritten dataset to a GS trainer (e.g., Brush, gsplat, LichtFeld)
   - Train for a few thousand iterations
   - Inspect the result: clean geometry? No operator ghosting? No artifacts at face boundaries?

4. **Round-trip validation:**
   - Take a cubemap face image, project it back to the fisheye space
   - Compare with the original fisheye image
   - Pixel values should match (within interpolation tolerance)

---

## Handling Different Camera Types

The pipeline should handle ALL camera types in a mixed dataset, not just equisolid fisheye:

| Input Camera Type | Action |
|-------------------|--------|
| Equisolid fisheye (>~160 deg FOV) | Split into 5 cubemap faces |
| Equidistant fisheye (>~160 deg FOV) | Split into 5 cubemap faces |
| Equidistant fisheye (<~120 deg FOV) | Maybe keep as single pinhole (undistort only) |
| Frame/pinhole | Keep as-is, just strip distortion if any |
| Equirectangular | Split into 6 cubemap faces (existing tooling) |

The threshold for "split vs. keep" depends on how much FOV you'd lose by converting to a single pinhole. Mike's docx focuses on the split case because that's where the current tooling gap is.

---

## Open Questions

1. **What camera model does Metashape write to cameras.txt for equisolid?** Alex has Metashape Pro and fisheye lenses — can answer this directly by exporting a test dataset:
   - Open a Metashape project with X5 equisolid fisheye alignment
   - File > Export > Export Cameras > COLMAP format
   - **Do not check "undistort images"**
   - Open the resulting `cameras.txt` and read the model string and parameter layout
   - Save the exported cameras.txt into `launchedpix/masking/` as a reference artifact
2. **Does Metashape's COLMAP export include undistorted images, distorted images, or both?** Check alongside question 1 — inspect the exported `images/` directory to see if images are modified or original.
3. **What does @gradeeterna's equirect-to-cubemap script look like?** Mike mentioned it in the docx. Getting access to it would inform the COLMAP I/O format decisions.
4. **What face size should we use?** Compute from source resolution, or use a fixed default? Mike's formula gives ~2445 for 8K equirect equivalence.
5. **Is point redistribution needed for the initial target?** Component 6 documents the full approach, but many GS trainers skip COLMAP's point data entirely. Decide whether the first deliverable targets GS-only (skip points) or full COLMAP consistency (rewrite points). Recommend: GS-only first, full rewrite as a follow-up.
6. **Rolling shutter compensation:** Mike mentions this as a motivation but it's not implemented. Does the COLMAP export from Metashape include rolling shutter metadata?

---

## Division of Labor (Suggested)

| Component | Lead | Notes |
|-----------|------|-------|
| COLMAP Parser | Shared | reconstruction-zone has a head start |
| Cubemap Geometry | Mike | Rotation math, face size computation |
| Image Remapping | Mike + Alex | Mike provides projection math, Alex integrates into pipeline |
| Mask Generation | Alex | reconstruction-zone pipeline |
| Mask Propagation | Alex | Remap through same LUT |
| COLMAP Writer | Shared | Format is simple, logic is straightforward |
| Point Redistribution | Shared | Deferred for GS-only first pass; needed for full COLMAP consistency |
| Validation | Alex | colmap_validation.py, visual QA, GS training test |

---

## Estimated Scale

For the SharkWipf dataset (100 frames, 2 X5 cameras, 4 lenses):

| Metric | Count |
|--------|-------|
| Source fisheye images | 400 |
| Cubemap face images | 2,000 |
| Cubemap face masks | 2,000 |
| Camera entries in cameras.txt | 1 (all X5 lenses use same face size) or 4 (one per lens) |
| Image entries in images.txt | 2,000 |
| Remap LUTs to compute | 4 (one per lens) x 5 (faces) = 20 |
| Remap LUTs to apply | 2,000 (images) + 2,000 (masks) = 4,000 |

Processing time estimate:
- Remap LUT computation: ~1 second per LUT = 20 seconds
- Image remapping: ~50ms per remap = ~200 seconds
- Mask generation (SAM3 on source): ~300ms per image = ~120 seconds
- Mask remapping: ~50ms per remap = ~100 seconds
- Total: ~8 minutes on GPU workstation

This is feasible for the demo dataset. Larger datasets (thousands of frames) would need the LUT caching optimization.
