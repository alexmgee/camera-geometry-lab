# Lens Boundary Mask Auto-Generation Plan

## Problem

Every fisheye image needs a lens boundary mask: which pixels contain valid image data vs. the black periphery outside the imaging circle. Currently these are hand-drawn PNGs. They should be derived from calibration data.

---

## Approach

Given a camera calibration (Metashape params or OpenCV K+D), auto-generate the lens boundary mask by computing where the valid image area ends.

### Method 1: Polar Angle Threshold

1. Compute ray directions for every pixel (Mike's Step 1 math)
2. Compute polar angle theta for each ray: `theta = arccos(Z_component)`
3. Threshold: pixels where theta exceeds a cutoff are invalid

**Advantages:**
- Directly tied to physics (the lens has a maximum field of view)
- Works for any projection model
- Cutoff can be set per-camera or auto-detected

**Determining the cutoff:**
- Mike measured ~103 degrees for the X5 (from the POLARANGLE_theta.png visualization)
- Can also be auto-determined: where the solid angle drops below a threshold
- Or from the image itself: where pixel intensity drops to near-zero (corroborating the geometric threshold)

### Method 2: Solid Angle Floor

1. Compute solid angle for every pixel (finite-difference cross product on ray field)
2. Threshold: pixels where solid angle is below some floor are invalid

**Advantages:**
- Catches both the circular boundary AND any dead zones within the image
- Solid angle approaching zero means the pixel contributes essentially nothing

**Disadvantages:**
- The threshold needs tuning (what's "too small"?)
- Edge pixels have noisy solid angle estimates due to gradient computation at boundaries

### Method 3: Image-Based (backup/validation)

1. Load the actual image
2. Detect the dark periphery (threshold on brightness)
3. Find the largest connected bright region
4. Morphological cleanup

**Advantages:**
- Doesn't need calibration data
- Catches manufacturing defects or sensor artifacts

**Disadvantages:**
- Scene-dependent (dark scene corners might be misclassified)
- Less precise than calibration-based

### Recommended: Combine Methods 1 + 3

Use polar angle threshold as the primary mask, then validate against the image-based detection. If they disagree significantly, flag for review.

---

## Resources

### Math (partially implemented)

**What Mike's educational scripts provide** (reference implementations):
- `Convert_Calibrated...py`, `undistort_points()` line 89: iterative distortion removal
- `Convert_Calibrated...py`, `equisolid_to_rays()` line 138: normalized image coords -> unit ray vectors
- `Convert_Calibrated...py`, `compute_solid_angle_fd()` line 194: finite-difference solid angle

**What camera-geometry-lab's package actually exposes** (verified against source):
- `distortion.py`: `undistort_points(xp, yp, calibration, iterations=8)` — takes a `MetashapeCalibration` dataclass, not raw K1-K4 args
- `rays.py`: `projected_coords_to_rays(x, y, model)` — dispatches to `pinhole_to_rays`, `equidistant_to_rays`, `equisolid_to_rays` based on model string. No top-level "compute_ray_field" that goes from calibration params to rays in one call.
- `solid_angle.py`: `compute_input_solid_angle(width, height, calibration, model)` — this IS a complete pixel-grid-to-solid-angle pipeline (builds pixel coords, undistorts, converts to rays, finite-difference cross product). This is the closest thing to a ready-to-use function for lens mask generation.
- `solid_angle.py`: `equirectangular_solid_angle_map(width, height)` — analytic, equirect only
- `models.py`: `MetashapeCalibration` dataclass, `ray_to_projection()` (forward), `validate_camera_model()`

**Gap: no single function for "calibration params -> ray field".**
The solid_angle module internally builds the full ray field (lines 32-43 of solid_angle.py) but doesn't expose it. A lens boundary mask tool would need either:
- (a) Extract the ray-field computation from `compute_input_solid_angle` into a reusable function in `rays.py` (e.g., `compute_ray_field(width, height, calibration, model) -> np.ndarray`)
- (b) Compute solid angle via `compute_input_solid_angle()` and threshold that directly (works, but doesn't give you theta for a polar angle threshold approach)
- (c) Duplicate the pixel-grid -> undistort -> model dispatch logic in the new lens mask module (not recommended)

Approach (a) is the cleanest: factor out the ray-field builder, then both `compute_input_solid_angle` and the new lens mask tool can call it.

### Sample Data for Testing

| Camera | Resolution | Model | Expected mask shape | Location |
|--------|-----------|-------|--------------------|---------| 
| X5 Cam1-Lens0 | 3840x3840 | equisolid | ~circular, ~206 deg FOV | `launchedpix/.../Insta360x5/Camera1/Lens0/` |
| Eagle | 4000x3000 | equidistant | wide oval | `launchedpix/SampleImages/Eagle/` |
| Insta360 OneR | 5312x3553 | equidistant | moderate oval | `launchedpix/SampleImages/Insta360OneR1inch/` |
| Nikon D800 | 7360x4912 | pinhole | full frame (all valid) | `launchedpix/SampleImages/NikonD80020mm/` |

### Existing Hand-Made Masks for Comparison

- `Eagle/1773019342.003189_mask.png`
- `Insta360OneR1inch/fullimagemask.png`
- `NikonD80020mm/fullmask.png`
- `Insta360x5/.../VID_..._lens0_ss412_3fps_0186_86.png`

---

## Where the Code Should Live

**Option A:** In `camera-geometry-lab/src/camera_geometry_lab/` as a new module (e.g., `lens_mask.py`)
- Pro: It uses the ray/solid_angle/distortion modules that are already there
- Pro: Natural fit -- it's a geometry operation, not a segmentation operation
- Con: Adds a dependency concern if reconstruction-zone wants to call it

**Option B:** In `reconstruction-zone/` as part of the masking pipeline
- Pro: Keeps all masking in one place
- Con: Duplicates or imports projection math from camera-geometry-lab

**Recommended:** Option A, with reconstruction-zone importing camera-geometry-lab as a dependency (or just copying the output mask files).

---

## Checklist

- [ ] Implement polar angle computation from calibration params (use existing `rays.py`)
- [ ] Determine theta cutoff for X5 (verify Mike's ~103 degree measurement)
- [ ] Implement solid angle floor detection (use existing `solid_angle.py`)
- [ ] Implement image-based dark periphery detection (OpenCV threshold + morphology)
- [ ] Combine polar angle + image-based for final mask
- [ ] Test against existing hand-made masks (pixel-level comparison, report IoU)
- [ ] Generate lens boundary masks for all 4 X5 lenses
- [ ] Verify: sum of solid angle within mask matches Mike's ~8.38 steradians for X5
- [ ] Add CLI entry point: `camera-geometry-lab lens-mask --config <config.json>`
- [ ] Document: how to use, what the threshold means, how to override
