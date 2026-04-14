# Cubemap Mask Propagation Validation: Hands-On Task List

Practical QA work to verify masks survive the fisheye-to-cubemap conversion correctly.

---

## Prerequisites

- [ ] X5 sample data accessible: `launchedpix/.../Insta360x5/Camera1/Lens0/`
- [ ] reconstruction-zone environment activated with SAM3 + YOLO26 available
- [ ] camera-geometry-lab environment activated
- [ ] ImageJ installed (for inspecting RAW float32 files)

---

## Task 1: Inventory the X5 Sample Data

- [ ] Confirm source image: `VID_20260407_102313_00_179_lens0_ss412_3fps_0186_86.jpg` (3840x3840)
- [ ] Confirm source mask: `VID_20260407_102313_00_179_lens0_ss412_3fps_0186_86.png`
- [ ] Confirm pre-computed geometry: `camera_equisolid_3840x3840_5054369d.raw` (5-band BSQ float32)
- [ ] Open the RAW file in ImageJ (Import->RAW, 3840x3840, 5 images, float32, little endian)
- [ ] Visually inspect each band: solid angle, qw, qx, qy, qz
- [ ] Check: does the solid angle band show a clean circular valid area?
- [ ] Check: do quaternion bands look smooth/continuous within the valid area?

## Task 2: Generate a Mask Using reconstruction-zone

- [ ] Load the X5 source image in reconstruction-zone
- [ ] Set geometry to FISHEYE (or DUAL_FISHEYE if applicable)
- [ ] Run SAM3 with prompts: "person", "tripod", "selfie stick" (or whatever's visible)
- [ ] Run YOLO26 as comparison
- [ ] Save the operator mask
- [ ] Visually compare with the provided lens boundary mask
- [ ] Create a combined mask (lens boundary AND operator)

## Task 3: Run Mike's Equirect Reprojection with Your Mask

- [ ] Run `Reproject_FEES_IMM_2_Equirectangular.py` with the X5 Cam1-Lens0 params
- [ ] Use your combined mask as mask1 input
- [ ] Compare output against Mike's existing `EquirectReprojection_image_color.png`
- [ ] Verify the mask reprojected correctly (check `EquirectReprojection_image_mask1.png`)
- [ ] Look for: mask edges aligned with image edges? Any leakage? Any gaps?

## Task 4: Run Mike's Cubemap Conversion

- [ ] Run `equi_2_cubefaces.py` with the X5 data
- [ ] Note: it uses the pre-computed RAW geometry file, not the calibration params directly
- [ ] Inspect all 5 cube face outputs (images + masks)
- [ ] Check for known issues:
  - [ ] Black pixel gaps from forward-splatting? (expected)
  - [ ] Mask edges aligned with image content?
  - [ ] Any face where the mask looks wrong (inverted, shifted, incomplete)?
- [ ] Document: which faces have issues, with screenshots

## Task 5: Run reconstruction-zone's Cubemap Decomposition (comparison)

**Note:** reconstruction-zone's CubemapProjection currently operates on equirectangular input, not raw fisheye. This task tests whether it could be adapted.

- [ ] Take Mike's equirect reprojection output as input
- [ ] Run it through reconstruction-zone's cubemap decomposition (6 faces)
- [ ] Run masking on each cubemap face independently
- [ ] Reproject face masks back to equirect
- [ ] Compare: is the round-trip mask consistent with the direct mask?
- [ ] Document differences and quality observations

## Task 6: Measure Mask Consistency

For each approach tested:
- [ ] Count total valid pixels in source mask
- [ ] Count total valid pixels across all cubemap face masks
- [ ] Are they close? (Should be similar but not identical due to resampling)
- [ ] Check cubemap face edges: do adjacent faces agree on mask values at shared boundaries?
- [ ] Use `graphically_combine_mask_and_image.py` to visualize mask boundaries on each face

## Task 7: Document Findings

- [ ] Create a summary of what worked, what didn't, what needs fixing
- [ ] Screenshots of each cubemap face (image + mask overlay)
- [ ] List of bugs or issues found in Mike's scripts
- [ ] List of gaps in reconstruction-zone's cubemap support for this use case
- [ ] Recommendations for the path forward (which cubemap approach to use)

---

## Expected Outcomes

- Concrete evidence of whether masks survive the fisheye -> cubemap round-trip
- Identification of the cx/cy centering bug's impact on mask alignment
- Understanding of where reconstruction-zone's cubemap decomposition needs equisolid support
- Screenshots and data that can go into the docx or be shared with Mike
