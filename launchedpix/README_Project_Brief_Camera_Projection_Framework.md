# Camera Projection Framework

## Project Brief

## Executive Summary

This project is evolving into a Python-based framework for working with calibrated camera models in a physically meaningful way. It started from a specific inversion problem for a distorted equisolid fisheye model, but it has expanded into a broader effort to represent multiple camera types consistently, compute per-pixel viewing geometry, and perform reprojection experiments between different image formats.

The central idea is to treat each pixel not just as a color sample, but as a geometric sample with:

- a ray direction in 3D
- a solid angle on the viewing sphere
- a known relationship to a calibrated camera model

That foundation then supports several downstream goals:

- inversion of calibrated lens models
- export of dense pixel-to-geometry mappings
- reprojection between fisheye, pinhole, equirectangular, cylindrical, and cube-based image layouts
- support for validity masks
- support for camera pose and spatial placement
- eventual viewer or analysis tooling built on top of these products

In short, the project is not only about undistortion. It is becoming a reusable geometry and reprojection toolkit for calibrated imaging systems.

---

## Why This Exists

The original problem was to invert a projection pipeline described in a manual, likely aligned with Agisoft Metashape-style calibration equations. The user wanted to start from image coordinates `(u, v)` in a distorted equisolid fisheye image and recover the underlying normalized coordinates `(x0, y0)`.

That request quickly expanded because `(x0, y0)` alone is not always the best long-term representation, especially for extreme wide-angle lenses. Once the discussion moved into fields of view above 180 degrees, spherical geometry, and reprojection into other formats, it became much more useful to think in terms of:

- unit ray directions
- projection-specific mappings to and from those rays
- per-pixel solid angle

The project now appears to serve two purposes at once:

- educational: understand calibrated projection models deeply and compare how they behave
- practical: build tools that can process real images, masks, and projection transforms in a reusable way

---

## Core Objective

Build a Python toolkit that can:

1. Describe multiple calibrated camera models in a unified way.
2. Map pixels to physically meaningful directional geometry.
3. Compute per-pixel solid angle.
4. Reproject images and masks across different projection types.
5. Store those geometric products in reusable file formats.
6. Extend naturally from single-camera image geometry to pose-aware multi-camera systems.

---

## High-Level Direction

The project is heading toward a common intermediate representation for images captured under different projection models.

Instead of treating each model separately all the way through the pipeline, the intended pattern is:

1. Start from a calibrated camera model and image pixels.
2. Invert those pixels into geometry.
3. Represent that geometry in a common form.
4. Use that common form to reproject or analyze the data.

The common form is increasingly defined by:

- unit ray directions
- per-pixel solid angle
- optional compact encodings such as quaternions
- associated validity masks

This is important because it makes reprojection a consequence of shared geometry rather than a pile of pairwise conversion scripts.

---

## Projection Models in Scope

The conversation explicitly moves toward support for:

- equisolid
- equidistant
- pinhole
- equirectangular
- cylindrical

It also explores derived output layouts such as:

- cube-face outputs
- vertex-centered three-face cube arrangements

These models are treated as different ways of sampling directions on the sphere rather than unrelated image types.

---

## Progress So Far

## 1. Inversion of a Distorted Equisolid Model

The project began with a forward projection pipeline roughly of the form:

`3D point -> normalized coordinates -> projected fisheye coordinates -> distorted coordinates -> image pixels`

The early work focused on deriving the reverse path:

`image pixels -> distorted normalized coordinates -> undistorted projected coordinates -> normalized camera coordinates`

Important progress made here:

- separation of intrinsics from distortion
- recognition that the distortion model is not analytically invertible in general
- adoption of an iterative undistortion solve
- explicit inversion of the equisolid mapping itself

This phase established the mathematical basis for the rest of the framework.

## 2. Dense Per-Pixel Mapping

After deriving the inversion, the conversation moved immediately into implementation. The goal became to compute the mapping for every pixel in the image and write those results to a file.

Outputs discussed at this stage:

- `u`
- `v`
- `x0`
- `y0`

This changed the work from symbolic math to dense numerical processing. It also made clear that the project is intended to generate reusable per-pixel data products, not just solve one point at a time.

## 3. Transition from `(x0, y0)` to Unit Rays

Once fields of view above 180 degrees came up, the limitations of a planar normalized-coordinate representation became more obvious. At that point, the project moved toward using full 3D unit ray directions as the preferred output.

This is one of the most significant conceptual upgrades in the thread.

Benefits of the shift to rays:

- avoids the awkwardness of planar coordinates for very wide fields of view
- gives a model-independent representation
- supports reprojection into any other projection type
- better reflects the physical meaning of the camera model

At this point the project stops being just an inverse-lens script and starts becoming a geometric camera abstraction.

## 4. Removal of the 180-Degree Assumption

The user explicitly wanted the framework to stop assuming a hard 180 degree limit. That means the project is not restricted to small-angle or even hemisphere-only use cases.

This matters for:

- full fisheye modeling
- direction-based representations
- custom remapping experiments
- robust handling of wide-angle lenses

The conversation reflects a deliberate effort to avoid a simplistic pinhole-centric view of camera geometry.

## 5. Cube-Face Reprojection Experiments

The project then moved into custom reprojection, especially mapping one distorted equisolid input image onto three pinhole-style cube faces meeting at a vertex.

This is not a standard six-face cubemap problem. It is a custom geometric configuration where:

- a single input camera is used
- the input optical axis points toward a cube vertex
- output images correspond to the three cube faces adjacent to that vertex

This indicates the project is interested in geometry-driven reprojection design, not only common off-the-shelf transforms.

## 6. Analytic Inverse Reprojection

Later in the thread, the reprojection pipeline was refined from slower or less direct approaches into an analytic inverse remapping approach.

Preferred pattern:

1. For each output pixel, compute its ray analytically.
2. Transform that ray into the input camera frame if needed.
3. Project the ray into the input camera model.
4. Sample image, mask, or geometry data from the input.

Why this matters:

- it scales better
- it is cleaner mathematically
- it avoids expensive direction-space search
- it makes reprojection a direct pixel-domain remap

This looks like the intended long-term computational strategy for the framework.

## 7. Solid Angle Computation

A major area of progress is the introduction of per-pixel solid angle as a first-class output.

This makes the project more than just a directional remapper. It brings in sampling density and radiometric meaning.

Solid angle products were discussed for:

- equisolid models with distortion
- equirectangular images
- reprojected outputs

The user also caught an important distinction:

- the solid angle of an output projection
- the solid angle of input camera samples after reprojection

That correction is significant. It shows the project is trying to preserve the meaning of the data, not just generate images that look correct.

## 8. Unified Multi-Model Representation

One of the clearest medium-term goals is a unified representation that works across different camera models.

The assistant proposed a RAW/BSQ format with multiple bands representing per-pixel geometry, including things like:

- direction
- quaternion-based forms
- solid angle

The conversation also includes helper utilities for:

- writing the data
- generating descriptive filenames
- parsing metadata such as image dimensions back out of the filename
- reading the raw files later

This suggests the project is converging on a data workflow, not just a math workflow.

## 9. Equirectangular Support

The framework was extended to equirectangular imagery so that it can participate as both:

- a source format
- a destination format

This is important because equirectangular acts as a natural hub representation for spherical imagery and reprojection. It is especially useful as an output space for comparing how different camera models map onto the sphere.

## 10. Reprojection of Images and Masks

Later requests move from pure geometry outputs into full reprojection of actual image data.

Inputs discussed:

- PNG or JPEG photographic images
- binary or grayscale masks describing valid pixels
- camera geometry data derived from calibration

Outputs discussed:

- reprojected color images
- reprojected masks
- output geometry maps such as solid angle and ray representations

This is an important transition from calibration analysis to working image-processing pipeline design.

## 11. Pose and Multi-Camera Extension

Near the end of the conversation, the user asks to introduce camera position and orientation in space, ideally using a commonly used convention such as COLMAP.

This extends the project from:

- single-camera model geometry

to:

- pose-aware camera systems
- multiple cameras in a shared spatial frame
- camera-to-world or world-to-camera transforms

This is the start of turning the framework into a real scene-level camera system rather than just an image-plane tool.

## 12. Additional Projection Transforms

The conversation ends by adding equirectangular-to-cylindrical and cylindrical-to-equirectangular conversions. This fits the broader direction well: once the geometry is framed in spherical terms, new projection transforms become natural additions.

---

## Current Conceptual Architecture

Even if not yet fully implemented as a polished library, the conversation points toward the following structure.

## A. Camera Model Layer

Each camera model needs to know how to:

- map geometry to image coordinates
- invert image coordinates back into geometry
- apply its projection equations
- handle distortion and undistortion
- define validity ranges or field-of-view limits

Examples:

- pinhole
- equidistant
- equisolid
- equirectangular
- cylindrical

## B. Shared Geometry Layer

This is the likely heart of the framework.

Shared outputs:

- unit ray direction per pixel
- per-pixel solid angle
- validity mask
- optional orientation encodings such as quaternion components

This layer makes different projection models interoperable.

## C. I/O and Storage Layer

The conversation repeatedly emphasizes reusable dense outputs.

Storage ideas already discussed:

- text tables for simple mappings
- RAW float32 files for dense multi-band geometry data
- BSQ-style layout for predictable loading
- filenames encoding metadata such as dimensions and model identifiers

## D. Reprojection Layer

This layer consumes:

- input image data
- input masks
- input camera model definition
- optional camera pose
- output camera model definition

It produces:

- reprojected images
- reprojected masks
- output geometry maps

## E. Scene / Pose Layer

This is still emerging, but it is clearly in scope.

Likely responsibilities:

- camera extrinsic parameters
- coordinate transforms between cameras
- alignment with conventions like COLMAP
- multi-camera workflows

---

## Key Technical Ideas That Appear To Be Settled

These ideas seem to be recurring design choices rather than temporary experiments.

### Use rays as the common geometric representation

The move from `(x0, y0)` to unit directions is a major throughline. It makes the system more stable, more general, and less tied to one projection family.

### Treat distortion inversion numerically when needed

The conversation accepts that full distortion inversion is not always closed-form and that iterative solutions are acceptable and expected.

### Prefer inverse remapping for reprojection

The analytic inverse reprojection approach appears to be the preferred strategy for efficiency and correctness.

### Make solid angle part of the standard output

Solid angle is not treated as an optional extra. It is becoming one of the main data products alongside ray direction.

### Use reusable file outputs

The user consistently asks for outputs that can be saved, reloaded, and used in later steps. That points toward a pipeline mentality rather than isolated scripts.

---

## Main Outputs The Project Is Working Toward

The framework appears to be producing or planning to produce:

- per-pixel normalized coordinate maps
- per-pixel unit ray direction maps
- quaternion representations of directions
- per-pixel solid-angle maps
- reprojected color images
- reprojected masks
- raw geometry files for downstream tools

These outputs are not just different file types. They represent the project’s attempt to separate:

- visual information
- validity information
- geometric information
- radiometric or sampling information

That separation is a strength.

---

## Practical Value of the Project

This framework could support several kinds of work.

### Geometry understanding

It helps explain what different camera models are doing and how they sample the sphere.

### Projection comparison

It allows direct comparison between how pinhole, equisolid, equidistant, equirectangular, and cylindrical models distribute pixels and solid angle.

### Reprojection experiments

It supports controlled remapping of images between camera models and layouts.

### Calibrated-image preprocessing

It can potentially be used to convert calibrated imagery into representations more suitable for downstream analysis or visualization.

### Future viewer or diagnostic tool

Because the outputs include both geometry and images, a future viewer could visualize:

- per-pixel ray direction
- solid angle
- mask coverage
- projection distortion
- cross-projection correspondences

---

## Likely Intended End State

The conversation suggests the long-term goal is something like this:

A modular Python framework in which a calibrated image can be turned into a dense geometric description, stored in a reusable format, and then reprojected or compared across multiple camera models and camera poses while preserving the physical meaning of each pixel.

That end state likely includes:

- a camera-model abstraction
- geometry generation
- reprojection utilities
- file readers and writers
- pose-aware transforms
- diagnostic and educational visualization later on

---

## Open Questions and Unresolved Design Areas

The conversation makes strong progress, but some areas still feel open or only partially specified.

### Exact package structure

The architecture is conceptually strong, but the conversation does not yet define a final module layout or API design.

### Canonical internal representation

Rays and solid angle are clearly central, but it is not yet fully settled whether the main internal storage is:

- XYZ vectors
- quaternions
- both

### File format standardization

RAW/BSQ outputs are discussed, but there may still be design decisions to make around:

- metadata storage
- naming conventions
- sidecar files
- coordinate conventions

### Pose conventions and handedness

Once multiple cameras and COLMAP-style poses enter the picture, conventions become critical:

- world-to-camera vs camera-to-world
- quaternion ordering
- axis directions
- handedness

This likely needs explicit normalization early to avoid confusion later.

### Resampling policy

The conversation discusses nearest-neighbor at points and later faster remapping, but some choices likely remain open:

- nearest vs bilinear vs higher-order interpolation
- treatment near invalid regions
- antialiasing for large reprojection changes

### Validity domains

Every camera model has a natural valid region. The framework likely needs a consistent way to define and propagate:

- valid pixels
- invalid rays
- clipped regions
- masked-out areas

---

## What To Discuss With a Colleague

If you are using this brief to get up to speed with a colleague quickly, these are probably the most important things to align on.

### 1. What is the canonical representation?

Is the project fundamentally organized around:

- pixels to rays
- pixels to rays plus solid angle
- a five-band or similar stored representation

This is probably the most important architectural question.

### 2. What camera models are first-class?

The conversation mentions several models. It would be useful to clarify which are considered core and which are extensions.

### 3. What is the authoritative calibration convention?

Much of the discussion assumes Agisoft Metashape-style equations. It would help to confirm exactly which convention governs:

- intrinsics
- distortion coefficients
- projection equations

### 4. What is the intended file contract?

If raw geometry products are already being used, clarify:

- file layout
- band ordering
- filename conventions
- whether metadata lives only in filenames or also elsewhere

### 5. What is the reprojection priority right now?

Possible priorities suggested by the conversation:

- accurate geometry first
- efficient inverse reprojection
- support for masks
- support for multiple camera poses
- preparation for a viewer later

### 6. What is already implemented versus still conceptual?

The conversation contains a lot of code-generation and design progress, but not all of it is necessarily integrated into one verified codebase yet. This is worth checking explicitly.

---

## Suggested Near-Term Milestones

If the goal is to turn the conversation into a stable working project, these seem like natural next steps.

### Milestone 1: Formalize the model abstraction

Define a common interface for all camera models:

- pixel to ray
- ray to pixel
- solid angle
- valid mask

### Milestone 2: Lock down conventions

Document:

- coordinate frames
- distortion parameter meanings
- pose conventions
- quaternion ordering
- image origin conventions

### Milestone 3: Standardize dense geometry outputs

Finalize:

- band layout
- file naming
- metadata handling
- loading helpers

### Milestone 4: Implement the general inverse reprojection engine

Make the reprojection pipeline model-agnostic so it can convert:

- camera model A to camera model B
- with masks
- with solid-angle outputs
- with optional pose transforms

### Milestone 5: Add verification and sanity checks

Useful checks include:

- ray normalization
- integrated solid-angle totals
- consistency of round trips
- agreement between analytic and numerical implementations

### Milestone 6: Build a small diagnostic viewer or report generator

Even a minimal viewer or plotting tool could accelerate development by making it easier to inspect:

- ray fields
- solid-angle maps
- mask coverage
- reprojection outputs

---

## Risks and Things Easy To Miss

There are several places where this kind of project can go subtly wrong.

### Convention drift

Different tools and models may use different axis directions, quaternion conventions, or projection definitions.

### Mixing geometric and radiometric outputs

A solid-angle map in the output projection is not the same as the reprojected input solid-angle contribution. The conversation already surfaced this exact issue.

### Implicit assumptions around FOV

Wide-angle models, especially beyond 180 degrees, can expose edge cases that are easy to hide if the framework quietly assumes a pinhole-like worldview.

### Validity masking

If valid and invalid regions are not handled consistently, reprojection outputs can look plausible while encoding incorrect correspondences.

### Lack of explicit metadata

Dense RAW formats are efficient, but they can become fragile if conventions are not documented and consistently enforced.

---

## Bottom Line

This project has already moved well beyond a one-off inverse-projection exercise. It is taking shape as a fairly sophisticated camera-geometry framework with strong emphasis on calibrated wide-angle models, per-pixel directional meaning, solid-angle-aware analysis, and flexible reprojection between multiple projection families.

The most important thing to understand is that the project’s true center is not any one camera model. It is the effort to build a common geometric language across camera models so that images, masks, and calibration data can all participate in a consistent pipeline.

If you are getting up to speed with a colleague, the best mental model is:

This is a projection and reprojection toolkit built around rays, solid angle, calibration, and dense pixel-level geometry, with the current work focused on turning several related scripts and mathematical derivations into a coherent system.

