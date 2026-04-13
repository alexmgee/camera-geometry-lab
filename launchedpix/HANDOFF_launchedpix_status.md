# launchedpix Handoff

## Purpose

This document is a practical handoff for the material currently sitting in [D:\Projects\camera-geometry-lab\launchedpix](</D:/Projects/camera-geometry-lab/launchedpix>).

It is written to help a teammate get up to speed quickly without having to reverse-engineer:

- what this folder contains
- what is conceptual versus actually implemented
- what the main script currently does
- how the sample outputs relate to the stated project direction
- what questions and next steps are likely most important

The short version is:

- this is **not yet a full repo or polished framework**
- it is currently a **working idea drop plus one main Python script**
- the materials combine:
  - an AI-generated design/conversation history
  - a broad conceptual project brief
  - one concrete reprojection script
  - several sample inputs and generated outputs
  - one adjacent research note about gravity-aware masking for 360 capture

---

## Executive Summary

The underlying project is about building a calibrated camera geometry and reprojection toolkit, with particular emphasis on wide-angle and fisheye imagery. The broad conceptual goal is to treat each image pixel as a geometric sample with:

- a ray direction
- a solid angle
- a known relation to a calibrated camera model

That common geometric representation is then intended to support:

- distortion-aware inversion
- reprojection between camera models
- comparison of different projection types
- image and mask remapping
- eventual pose-aware multi-camera workflows

However, the **actual implementation present in `launchedpix` is much narrower than the long-term vision**.

Today, the folder mainly contains:

- a long ChatGPT conversation transcript describing the evolution of the ideas
- a polished project brief derived from that conversation
- one concrete script that reprojects calibrated input imagery from several input camera models into **equirectangular output**
- sample input images, masks, and generated outputs for three example cameras
- a separate planning note about operator masking for 360 reconstruction using gravity-aware coordinate handling

So the most useful mental model is:

This folder is a **prototype / research handoff package**, not yet a structured codebase.

---

## Folder Inventory

Top-level contents under [launchedpix](</D:/Projects/camera-geometry-lab/launchedpix>):

- [Reproject_FEES_IMM_2_Equirectangular.py](</D:/Projects/camera-geometry-lab/launchedpix/Reproject_FEES_IMM_2_Equirectangular.py>)
  Main working script. This is the most important implementation artifact.

- [Invert-Projection-Equations_chatgpt-convo.md](</D:/Projects/camera-geometry-lab/launchedpix/Invert-Projection-Equations_chatgpt-convo.md>)
  Full Markdown transcript of the source ChatGPT conversation.

- [README_Project_Brief_Camera_Projection_Framework.md](</D:/Projects/camera-geometry-lab/launchedpix/README_Project_Brief_Camera_Projection_Framework.md>)
  Expanded narrative brief describing the intended project direction.

- [conversation-timeline.md](</D:/Projects/camera-geometry-lab/launchedpix/conversation-timeline.md>)
  Despite the filename, this is **not** a turn-by-turn timeline. It is a shorter narrative project brief.

- [convert_chatgpt_mhtml_to_markdown.py](</D:/Projects/camera-geometry-lab/launchedpix/convert_chatgpt_mhtml_to_markdown.py>)
  Utility script used to convert the ChatGPT `.mhtml` export into Markdown. Not core project logic.

- [InvertProjectionEquations_webpagesinglefile.mhtml](</D:/Projects/camera-geometry-lab/launchedpix/InvertProjectionEquations_webpagesinglefile.mhtml>)
  Original saved ChatGPT webpage export.

- [InvertProjectionEquations_webpagesinglefile.pdf](</D:/Projects/camera-geometry-lab/launchedpix/InvertProjectionEquations_webpagesinglefile.pdf>)
  PDF export of the same conversation.

- [turn-05-user-image-1.png](</D:/Projects/camera-geometry-lab/launchedpix/turn-05-user-image-1.png>)
  The uploaded equation image from the original conversation.

- [SampleImages](</D:/Projects/camera-geometry-lab/launchedpix/SampleImages>)
  Three example datasets with input imagery, masks, and generated reprojection outputs.

- [OSV research with gravity](</D:/Projects/camera-geometry-lab/launchedpix/OSV%20research%20with%20gravity>)
  Separate planning note about operator masking for 360 reconstruction using gravity-aware coordinate systems.

---

## What Is Actually Implemented Today

## Main implemented artifact

The concrete implementation currently present is the single script:

[Reproject_FEES_IMM_2_Equirectangular.py](</D:/Projects/camera-geometry-lab/launchedpix/Reproject_FEES_IMM_2_Equirectangular.py>)

This script is best understood as:

- a prototype educational reprojection tool
- intended to transform calibrated input imagery into **equirectangular output**
- able to compute both output-space and reprojected input-space solid-angle data
- able to generate a dense raw geometry product for the output equirectangular image

The script header is explicit that it is:

- mostly AI-written
- educational in purpose
- not guaranteed correct
- something the author advises using cautiously

That caveat matters. The current implementation should be treated as a promising prototype, not as a validated production pipeline.

## Input camera models currently supported

The script supports these **input** projection types:

- `pinhole`
- `equidistant`
- `equisolid`

It reprojects those inputs into:

- `equirectangular` output

So while the broader project brief talks about a more general multi-model framework, the current code is much more specific:

**input camera -> equirectangular output**

## Core functions present in the script

The script currently includes the following main computational pieces:

- `distort_points(...)`
  Applies forward distortion.

- `undistort_points(...)`
  Iteratively removes distortion.

- `ray_to_projection(...)`
  Maps rays to model-specific projected coordinates for `pinhole`, `equidistant`, and `equisolid`.

- `equirectangular_rays(...)`
  Builds the output equirectangular ray field.

- `pinhole_to_rays(...)`
- `equidistant_to_rays(...)`
- `equisolid_to_rays(...)`
  Convert model-specific projected coordinates into unit rays.

- `compute_input_solid_angle(...)`
  Numerically estimates per-pixel solid angle in the input camera model.

- `reproject_fast(...)`
  Main inverse reprojection routine.

## Main reprojection behavior

The current reprojection pipeline is:

1. Load a calibrated input image.
2. Optionally load one or two masks.
3. Build an output equirectangular pixel grid.
4. Convert each output pixel to a ray.
5. Project each ray into the input camera model.
6. Apply distortion and convert to input pixel coordinates.
7. Use OpenCV `remap()` to sample the input image and masks.
8. Compute an output equirectangular solid-angle map.
9. Compute the input camera’s solid-angle map and reproject that into output space.
10. Save image, masks, and raw geometry outputs.

This is a sensible inverse-mapping design and aligns with the broader conceptual direction discussed in the conversation.

---

## What The Script Outputs

Given an input image and model parameters, the script produces:

- reprojected color image
- reprojected mask image(s), if supplied
- equirectangular RAW geometry file
- reprojected input solid-angle RAW file

### PNG outputs

Examples:

- `EquirectReprojection_color.png`
- `EquirectReprojection_mask1.png`
- `EquirectReprojection_mask2.png` if a second mask is provided

### Equirectangular RAW output

The script writes:

- `*_equirectangular.raw`

This file is written as float32 BSQ-style data with 5 bands.

According to the script comments, the bands are:

1. output equirectangular solid angle
2. quaternion `w`
3. quaternion `x`
4. quaternion `y`
5. quaternion `z`

The quaternion is constructed from the output ray field and appears intended to encode the rotation from the +Z axis to each ray direction.

### Reprojected input solid-angle RAW output

The script separately writes:

- `*_input_solid_angle.raw`

This is the input camera’s per-pixel solid angle, numerically estimated in the original model and then reprojected into the output equirectangular layout.

This distinction is important:

- `*_equirectangular.raw` contains the **output projection’s own pixel solid angle**
- `*_input_solid_angle.raw` contains the **input camera’s solid angle after remapping into output space**

That distinction was a major correction in the ChatGPT discussion and appears to be reflected in the script.

---

## Sample Data Currently Present

There are three example input datasets under [SampleImages](</D:/Projects/camera-geometry-lab/launchedpix/SampleImages>):

- [Eagle](</D:/Projects/camera-geometry-lab/launchedpix/SampleImages/Eagle>)
- [Insta360OneR1inch](</D:/Projects/camera-geometry-lab/launchedpix/SampleImages/Insta360OneR1inch>)
- [NikonD80020mm](</D:/Projects/camera-geometry-lab/launchedpix/SampleImages/NikonD80020mm>)

Each directory contains:

- an input image
- one input mask
- a reprojected output image
- a reprojected mask
- a reprojected input solid-angle raw file
- a zipped and/or expanded equirectangular raw geometry output

### Observed output structure

For each example, the equirectangular outputs appear to be generated at:

- width `7680`
- height `3840`

This can be inferred from the output file sizes:

- `*_equirectangular.raw` is `589,824,000` bytes
- `*_input_solid_angle.raw` is `117,964,800` bytes

Those match:

- `7680 * 3840 * 5 * 4` bytes for the 5-band float32 geometry file
- `7680 * 3840 * 1 * 4` bytes for the single-band float32 solid-angle file

### Example datasets

#### Eagle

Files under [SampleImages\Eagle](</D:/Projects/camera-geometry-lab/launchedpix/SampleImages/Eagle>):

- input image: `1773019342.003189.jpg`
- input mask: `1773019342.003189_mask.png`
- equirect color output
- mask output
- reprojected input solid-angle raw
- zipped and expanded equirectangular raw geometry

The active `__main__` example in the script is currently set to run the **Eagle** example.

#### Insta360 One R 1-inch

Files under [SampleImages\Insta360OneR1inch](</D:/Projects/camera-geometry-lab/launchedpix/SampleImages/Insta360OneR1inch>):

- input image: `IMG_20210522_062640_00_664.jpg`
- input mask: `fullimagemask.png`
- corresponding equirect reprojection outputs

The script includes a commented example block for this dataset using an `equidistant` camera model.

#### Nikon D800 20mm

Files under [SampleImages\NikonD80020mm](</D:/Projects/camera-geometry-lab/launchedpix/SampleImages/NikonD80020mm>):

- input image: `DSC_4597-Enhanced.jpg`
- input mask: `fullmask.png`
- corresponding equirect reprojection outputs

The script includes a commented example block for this dataset using a `pinhole` camera model.

---

## What Is Conceptual vs What Is In Code

This is probably the most important distinction for a teammate.

## Implemented in the current script

- inverse reprojection from input camera models to equirectangular
- support for `pinhole`, `equidistant`, `equisolid` inputs
- one or two masks as optional inputs
- equirectangular output ray/quaternion and solid-angle data
- reprojected input solid-angle output
- example parameter blocks for three datasets

## Discussed extensively in the conversation, but not clearly implemented here as a full system

- a general multi-model framework beyond equirectangular output
- a clean package/module architecture
- generic camera-model abstractions
- reusable CLI or library API
- robust file format specification beyond comments and naming
- multi-camera pose/extrinsics integration
- COLMAP-style camera pose handling
- equirectangular-to-cylindrical and cylindrical-to-equirectangular conversion as reusable tools
- cube-face generation pipelines
- a viewer or app layer

In other words:

The **conversation and briefs describe the destination**.

The **single script shows one important but narrower prototype path toward it**.

---

## Existing Documentation and How To Read It

## 1. Full conversation transcript

[Invert-Projection-Equations_chatgpt-convo.md](</D:/Projects/camera-geometry-lab/launchedpix/Invert-Projection-Equations_chatgpt-convo.md>)

Use this if you want the full history of how the ideas evolved. It is long, but it contains the reasoning behind:

- inversion of the original equations
- the move from normalized coordinates to rays
- solid-angle interpretation
- reprojection design
- broader ideas like cubemaps, cylindrical transforms, and pose support

This is best treated as a design conversation, not a specification.

## 2. Expanded project brief

[README_Project_Brief_Camera_Projection_Framework.md](</D:/Projects/camera-geometry-lab/launchedpix/README_Project_Brief_Camera_Projection_Framework.md>)

This is the best narrative summary of the broader vision. It is long, but it is organized and useful for understanding:

- what the project is really trying to become
- why rays and solid angle are central
- which camera models are in scope
- what major conceptual milestones were reached in the conversation

## 3. Misnamed timeline file

[conversation-timeline.md](</D:/Projects/camera-geometry-lab/launchedpix/conversation-timeline.md>)

Despite the filename, this is not a strict timeline. It is effectively a shorter narrative brief. A teammate should not expect it to be a concise chronology of decisions.

## 4. Conversion utility

[convert_chatgpt_mhtml_to_markdown.py](</D:/Projects/camera-geometry-lab/launchedpix/convert_chatgpt_mhtml_to_markdown.py>)

This is simply a helper for turning the saved ChatGPT webpage into Markdown. It is useful for provenance, but it is not part of the camera-model logic.

---

## Adjacent Research Thread: OSV / Gravity / Operator Masking

The folder [OSV research with gravity](</D:/Projects/camera-geometry-lab/launchedpix/OSV%20research%20with%20gravity>) contains:

- [360_masking_pipeline_working_plan.docx.md](</D:/Projects/camera-geometry-lab/launchedpix/OSV%20research%20with%20gravity/360_masking_pipeline_working_plan.docx.md>)

This is related but distinct from the current reprojection script.

### What it covers

It outlines a plan for masking out the camera operator in 360 imagery prior to reconstruction, especially for:

- COLMAP
- 3D Gaussian Splatting
- DJI Osmo 360 / OSV-based workflows

### Central idea

The note argues that gravity correction in stitched 360 imagery makes the operator move unpredictably in equirectangular space, even though the operator may be relatively fixed in the camera body frame.

The proposed solution is to:

- extract per-frame orientation quaternions from `.osv` footage
- undo gravity alignment to produce a body-frame ERP
- estimate the operator direction there
- render a crop centered on the operator
- segment the operator in this normalized view
- map the mask back to the gravity-corrected ERP used by downstream tools

### Why it matters in this handoff

This note is not just random extra material. It suggests a future direction where:

- the camera geometry / reprojection work in the main script
- and the body-frame / gravity-aware masking work

could eventually connect.

A teammate should likely treat this as an adjacent pipeline concept that may later depend on the same projection and ray machinery.

---

## Important Caveats and Limitations

Several constraints are visible directly in the code and comments.

## 1. This is prototype-quality, not validated production code

The script header explicitly says correctness is not assured.

That warning should be taken seriously.

## 2. Resampling quality is intentionally simple

The current script uses:

- nearest-neighbor remapping

This is fine for fast experiments and some mask use cases, but it will likely limit image quality for real production reprojection.

## 3. There is no CLI or package structure yet

The script is driven by editing `__main__` manually. This means:

- no installable package
- no reusable command-line interface
- no argument parsing
- no obvious automated workflow

## 4. One visible bug is already noted by the author

The header comment mentions a bug when remapping `pinhole` imagery:

- two output images
- a halo around the center image

This likely needs investigation if pinhole support is important.

## 5. Broader project scope exceeds the current implementation

The design conversation covers many things that are not yet codified here as a unified framework.

## 6. No obvious tests or verification harness

There is currently no visible test suite, no quantitative validation notebook, and no clearly documented acceptance criteria in this folder.

---

## Best Current Understanding of the Project Direction

Based on the docs and the script together, the project seems to be heading toward a framework with these layers:

## A. Camera model definitions

Each model knows how to map between:

- image coordinates
- projection coordinates
- ray directions

and how to apply or invert distortion.

## B. Shared dense geometry products

Per-pixel outputs such as:

- unit rays
- solid angle
- masks
- possibly quaternion forms

become the common language between camera models.

## C. Reprojection engine

A generic inverse-mapping engine would then allow:

- model A -> model B
- image reprojection
- mask reprojection
- potentially pose-aware remapping

## D. Scene / pose layer

This is more aspirational in the current material, but the conversation clearly points toward:

- extrinsics
- COLMAP-style pose conventions
- multi-camera spatial transforms

## E. Visualization / downstream use

The eventual outputs could support:

- analysis of sampling density
- geometric debugging
- preprocessing for reconstruction
- future viewer tooling

---

## Recommended Reading Order For A New Teammate

If someone is new to this work, this is probably the fastest useful order:

1. Read [README_Project_Brief_Camera_Projection_Framework.md](</D:/Projects/camera-geometry-lab/launchedpix/README_Project_Brief_Camera_Projection_Framework.md>)
   Use it to understand the broader intended system.

2. Skim [Reproject_FEES_IMM_2_Equirectangular.py](</D:/Projects/camera-geometry-lab/launchedpix/Reproject_FEES_IMM_2_Equirectangular.py>)
   Focus on what is truly implemented.

3. Inspect one sample directory such as [SampleImages\Eagle](</D:/Projects/camera-geometry-lab/launchedpix/SampleImages/Eagle>)
   This makes the outputs concrete.

4. Use [Invert-Projection-Equations_chatgpt-convo.md](</D:/Projects/camera-geometry-lab/launchedpix/Invert-Projection-Equations_chatgpt-convo.md>) as reference when a design choice in the script seems unclear.

5. Read the OSV masking plan separately if the 360 operator-masking workflow is relevant to current priorities.

---

## Questions Worth Aligning On With The Colleague

These are the most important questions to resolve early.

### 1. What should count as the canonical representation?

Is the real center of the system:

- rays only
- rays plus solid angle
- a standard 5-band raw geometry product
- something else

### 2. What part of the broad vision is the immediate priority?

Possible near-term priorities implied by the material:

- make the equirectangular reprojection path reliable
- generalize the script into a reusable camera-model framework
- add proper pose/extrinsics support
- support masking / body-frame 360 workflows
- improve image quality beyond nearest-neighbor

### 3. Which models are first-class for current work?

The conceptual materials mention many models, but the actual code currently centers on:

- pinhole
- equidistant
- equisolid
- equirectangular output

Clarifying the “must support now” set will help avoid scope creep.

### 4. What is the expected correctness standard?

Should this be:

- educational and exploratory
- accurate enough for research analysis
- trusted for preprocessing real reconstruction pipelines

That choice affects how much validation is needed next.

### 5. What should become a proper repo structure?

Right now the folder is a mix of:

- docs
- generated artifacts
- inputs
- outputs
- one script

If the work continues, it likely needs clearer separation:

- `src`
- `data` / `examples`
- `docs`
- `tests`
- maybe notebooks or validation reports

### 6. How tightly related is the OSV masking work to the current reprojection work?

The connection seems strong, but the integration boundary is not yet explicit.

---

## Suggested Near-Term Next Steps

If the next step is to turn this into something easier to maintain collaboratively, these would be sensible priorities.

## 1. Decide what is in scope for the next milestone

For example:

- only “input model to equirectangular” hardening
- or a true general camera-model abstraction

## 2. Turn the current script into a small module structure

Natural split:

- projection models
- distortion
- ray generation
- solid-angle calculations
- reprojection
- file I/O

## 3. Add a reproducible command-line entry point

Instead of editing `__main__`, make the script runnable with explicit arguments for:

- input image
- masks
- model type
- calibration parameters
- output prefix
- output width

## 4. Add verification checks

Examples:

- ray normalization
- expected equirectangular solid-angle totals near `4π`
- sanity checks on output dimensions
- known sample-case validation

## 5. Clarify the file-format contract

Especially:

- exact band ordering
- coordinate conventions
- quaternion meaning and ordering
- filename conventions
- whether metadata needs a sidecar file

## 6. Decide whether the gravity-aware 360 masking work is the next branch of effort

If yes, it may make sense to reuse the same spherical reprojection machinery rather than start a separate geometry stack.

---

## Bottom Line

The `launchedpix` folder is best understood as a strong exploratory handoff package.

It already contains:

- a clear long-term vision
- the reasoning trail behind that vision
- one meaningful prototype implementation
- several generated sample outputs
- one adjacent research branch for 360 operator masking

What it does **not** yet contain is a fully organized, validated, general-purpose repo.

So the right framing for a teammate is:

There is already enough here to understand the intended geometry pipeline and to run or study a real prototype, but turning it into a robust collaborative project will require narrowing the next milestone, clarifying conventions, and separating the broad conceptual roadmap from the specific code that exists today.


