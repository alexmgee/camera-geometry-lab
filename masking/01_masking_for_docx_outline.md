# Masking Section for ColeMapMultiCameraPinholeConversion.docx

Response to Mike's acknowledged gap: "I have not commented on, and don't plan to comment on how to obtain them other than saying either by hand or some AI segmentation tool."

This outlines a proposed section to add to the document, covering what masks are, why they matter, how they're made, and how they propagate through the pipeline.

---

## Proposed Section: "Masking: Identifying Valid and Invalid Pixels"

### 1. Why Masking Matters for Gaussian Splat Training

- GS training treats every pixel as a training signal. Invalid pixels (outside the lens circle, containing the operator/equipment) corrupt the reconstruction.
- Masked pixels are excluded from the loss function during training. Without masks, the splat learns to reproduce the photographer as part of the scene.
- Masking quality directly limits reconstruction quality. A mask that's too tight clips valid scene data. A mask that's too loose lets artifacts through.

### 2. Two Types of Masks

#### 2a. Lens Boundary Masks ("Where is the valid image area?")

- Fisheye lenses project a circular image onto a rectangular sensor. Pixels outside the circle are black/invalid.
- The boundary is not a perfect circle due to manufacturing, sensor alignment, and lens distortion.
- Can be derived from calibration data:
  - From the solid angle map: pixels where solid angle approaches zero
  - From the polar angle: pixels where theta exceeds the lens's half-angle (e.g., ~103 degrees for X5 = ~206 degree FOV)
- Can also be derived from the image itself (threshold the dark periphery), but calibration-based is more precise and consistent across frames.
- For frame/pinhole cameras: the entire sensor is typically valid, so the mask is all-ones unless there's vignetting to exclude.

#### 2b. Operator/Equipment Masks ("What should be removed from the scene?")

- 360 cameras always capture the operator: the person holding the camera, tripod legs, selfie sticks, shadows.
- Even non-360 setups may capture equipment at the edges of wide-angle lenses.
- These must be segmented and masked to prevent them from appearing in the Gaussian Splat.
- Approaches (from simplest to most capable):
  - **Manual annotation**: Draw masks by hand in an image editor. Accurate but doesn't scale.
  - **Class-based detection (YOLO26)**: Fast (~15ms/image), detects known COCO classes (person, backpack, umbrella). Limited to trained categories.
  - **Text-prompted segmentation (SAM 3 / SAM 3.1)**: Prompt with "person", "tripod", "selfie stick". Handles novel objects. ~300ms/image.
  - **Ensemble**: Run multiple models and fuse results for higher reliability.
  - **Temporal propagation**: For video sequences, propagate masks across frames using SAM 3.1's Object Multiplex (multi-object tracking in one forward pass) or dedicated VOS models. Avoids re-segmenting every frame from scratch.
- Shadow detection: The operator casts shadows that should also be masked. Can be detected with brightness heuristics or ML-based shadow detectors.

### 3. How Masks Flow Through the Pipeline

#### In the current pipeline (Steps 1-3):
- Masks are loaded alongside images as grayscale PNGs (0 = invalid, nonzero = valid)
- At every reprojection step, masks are remapped using the same coordinate mapping as the image, with nearest-neighbor interpolation (to keep them binary)
- The solid angle computation in Step 1 can use the mask to exclude invalid pixels
- The COLMAP parameter fitting (Convert_SARayDirQuaternion script) uses the mask to select which pixels participate in the optimization
- The cubemap conversion (equi_2_cubefaces.py) skips masked pixels entirely

#### In Step 4 (COLMAP dataset rewrite):
- Each source fisheye image has one combined mask (lens boundary + operator)
- When the image is split into 5 cubemap faces, the mask splits the same way
- Each cubemap face image (`frame_001_face_PZ.png`) gets a corresponding mask (`frame_001_face_PZ_mask.png`)
- GS training software reads both and excludes masked pixels from the loss

### 4. Quality Considerations

- **Mask-too-tight**: Valid scene data excluded. Missing geometry in the splat, especially at edges.
- **Mask-too-loose**: Invalid data included. Operator ghosting, equipment artifacts in the splat.
- **Temporal inconsistency**: If masks flicker frame-to-frame, the splat gets conflicting training signals.
- **Edge precision**: A hard binary mask at 1-pixel precision is usually sufficient. Alpha matting (soft edges) is sometimes used but most GS trainers expect binary masks.
- **Human review**: Even the best automated pipeline needs a review step. A thumbnail grid showing mask overlays with accept/reject/edit workflow catches problems before they reach training.

### 5. Scale

- 100 frames x 4 lenses (dual X5 setup) x 5 cubemap faces = 2,000 images + 2,000 masks
- Automated masking is not optional at this scale
- Processing time estimate: SAM 3 at ~300ms/image on source fisheyes = ~120 seconds for 400 source images. Cubemap mask splitting is just remapping (fast). Total under 5 minutes on a GPU workstation.

### 6. Available Tooling

Brief mention of reconstruction-zone as the masking component:
- Multi-model segmentation (SAM3, SAM 3.1, YOLO26, RF-DETR, FastSAM)
- Geometry-aware processing (adapts to equirectangular, fisheye, pinhole)
- Cubemap decomposition for equirectangular masking
- COLMAP geometric validation of masks against sparse reconstruction
- Interactive review/correction GUI
- Temporal consistency across video frames

---

## Notes for drafting

- Tone should match Mike's document: educational, first-person, practical
- Include screenshots where possible (mask overlay examples, cubemap face masks)
- Reference the specific scripts by name where they consume masks
- Keep the section self-contained so Mike can paste it into the docx with minimal editing
