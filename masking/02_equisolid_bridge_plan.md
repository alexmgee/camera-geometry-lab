# Equisolid Model Bridge Plan

## Problem

Mike's projection pipeline uses the Metashape equisolid fisheye model with 11 parameters:
```
(f, cx, cy, K1, K2, K3, K4, P1, P2, B1, B2)
```

reconstruction-zone's `fisheye_reframer.py` currently uses the **equidistant** fisheye model with OpenCV-style matrices:
```
camera_matrix K (3x3) + dist_coeffs D (4-element)
```

These are different projection functions. Connecting them lets reconstruction-zone's masking pipeline work directly on Mike's camera data.

---

## Projection Model Comparison

### Equidistant (what reconstruction-zone uses now)
```
r = f * theta
```
Where theta is the angle from the optical axis and r is the distance from the image center.

- Linear relationship between angle and radius
- Used by OpenCV's fisheye module
- Common in older fisheye calibrations

### Equisolid (what the Insta360 X5 and most modern 360 cameras use)
```
r = 2f * sin(theta / 2)
```

- Preserves solid angle (area on the sphere maps proportionally to area on the sensor)
- Used by Metashape for 360 camera fisheye lenses
- The X5 has ~206-degree FOV, making the model choice significant at extreme angles

### At what angles does the difference matter?

| Theta (deg) | Equidistant r/f | Equisolid r/f | Difference |
|-------------|-----------------|---------------|------------|
| 30          | 0.524           | 0.518         | 1.2%       |
| 60          | 1.047           | 1.000         | 4.7%       |
| 90          | 1.571           | 1.414         | 11.1%      |
| 100         | 1.745           | 1.532         | 13.9%      |
| 103         | 1.798           | 1.572         | 14.4%      |

At the edge of the X5's FOV (~103 degrees), using the wrong model puts pixels 14% off in radius. That's significant.

---

## What Needs to Change

### In camera-geometry-lab (src/)

**Already done:** `models.py` and `distortion.py` handle equisolid. No changes needed here.

### In reconstruction-zone

#### 1. Add equisolid projection to `fisheye_reframer.py`

Currently the reframer uses `cv2.fisheye.initUndistortRectifyMap()` which assumes equidistant. For equisolid, we need custom projection math.

**Source for the math** (verified, from Mike's scripts):
- Forward (ray -> image): `r = 2f * sin(theta/2)`, then apply distortion, then pixel coords
  - File: `Reproject_FEES_IMM_2_Equirectangular.py`, `ray_to_projection()` line 138-164
  - File: `Reproject_FEES_IMM_2_Equirectangular.py`, `distort_points()` line 118-132
- Inverse (image -> ray): pixel coords -> undistort -> `theta = 2 * arcsin(r/2)`, then ray vector
  - File: `Convert_Calibrated...py`, `equisolid_to_rays()` line 138-149
  - File: `Convert_Calibrated...py`, `undistort_points()` line 89-107

#### 2. Add Metashape parameter import

Parse the 11-parameter tuple format into a calibration object that reconstruction-zone can use.

**Input format** (from Metashape XML or Mike's scripts):
```xml
<calibration type="equisolid_fisheye" class="adjusted">
  <resolution width="3840" height="3840"/>
  <f>1038.8800662053641</f>
  <cx>21.881278610058398</cx>
  <cy>-7.026678990019831</cy>
  <k1>0.053306304106176199</k1>
  <k2>0.044439313326053206</k2>
  <k3>-0.012265277168873235</k3>
  <p1>-0.00036101703821687974</p1>
  <p2>-0.00012934918088242859</p2>
</calibration>
```

**Output:** A calibration object compatible with reconstruction-zone's `FisheyeCalibration` dataclass, extended with:
- Projection model type (`equidistant` or `equisolid`)
- The full Metashape parameter set (K1-K4, P1-P2, B1-B2)

#### 3. Custom remap for equisolid cubemap extraction

Instead of using `cv2.fisheye.initUndistortRectifyMap()`, build the remap LUT directly:
- For each output cubemap face pixel, compute the 3D ray direction
- Project that ray into the source fisheye image using equisolid + distortion
- Store as `map_x, map_y` for `cv2.remap()`

This is the inverse-mapping approach (output pixel -> source pixel), which is how the existing equirect reprojection works and how reconstruction-zone's cubemap decomposition works.

---

## Reference Calibration Data (from Mike's delivery)

### Insta360 X5 (all 4 lenses)

| Sensor | f | cx | cy | k1 | k2 | k3 |
|--------|---|----|----|----|----|-----|
| Cam1-Lens0 | 1038.88 | 21.88 | -7.03 | 0.0533 | 0.0444 | -0.0123 |
| Cam1-Lens1 | 1041.82 | 7.06 | -5.78 | 0.0475 | 0.0488 | -0.0130 |
| Cam2-Lens3 | 1037.06 | 21.74 | -17.02 | 0.0499 | 0.0467 | -0.0127 |
| Cam2-Lens4 | 1034.50 | 2.27 | 6.39 | 0.0553 | 0.0389 | -0.0100 |

### 3DMakerPro Raven (equisolid, left + right)

| Sensor | f | cx | cy |
|--------|---|----|----|
| Left | 1126.21 | -64.80 | -18.20 |
| Right | 1126.02 | 48.11 | 70.99 |

---

## Checklist

- [ ] Understand the Metashape distortion ordering (K1-K4 radial, P1-P2 tangential, B1-B2 affinity)
- [ ] Verify: does camera-geometry-lab's `distortion.py` match Mike's `undistort_points()` exactly?
- [ ] Implement equisolid ray-to-pixel projection (forward direction) for remap LUT generation
- [ ] Implement Metashape XML calibration parser (or 11-param tuple parser)
- [ ] Add `projection_model` field to reconstruction-zone's `FisheyeCalibration` dataclass
- [ ] Build equisolid-aware remap LUT for cubemap face extraction
- [ ] Test with X5 Cam1-Lens0 sample data from this delivery
- [ ] Compare output against Mike's equirect reprojection output (visual sanity check)
- [ ] Verify solid angle sum for masked X5 lens matches Mike's reported ~8.38 steradians
