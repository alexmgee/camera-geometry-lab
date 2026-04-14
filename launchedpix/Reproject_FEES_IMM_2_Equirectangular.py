##############################################################################################
#
# Program: Reproject_FEES_IMM_2_Equirectangular.py
# Author: Mike Heath  (but mostly AI)
# Date: 4/6/2026
#
# Disclaimer: I really have NO assurance that this program is correct. Initial runs seemed to
# produce sensible results to me, but I strongly advise caution in using it: !USE AT YOUR OWN RISK!
#
# Purpose:
#
# I've been thinking about the qualities and capabilities of different cameras, rigs of 
# cameras and conversions of data for processing imagery for 3D modeling. There are established
# pipelines of processing data from different types of cameras for both photogrammetry and
# Gaussian Splatting. Those processing chains can be long and involve various software packages
# different conventions and many choices of parameters and image conversions to different lens models.
#
# My goal here was to set up some image transformations between different projections, well,
# really just outputting Equirectangular projection data. Inputs could be Frame (including pinhole),
# Equidistant and Equisolid. The image quality of the output images are probably NOT VERY GOOD because
# I just used NEAREST NEIGHBOR RESAMPLING.
#
# The programs purpose is MORE EDUCATIONAL than an image preprocessing step for 3D modeling.
#
# In a nutshell you can think of this all as "undistort to Equirectangular". But show me the solid
# angles of the output equirectangular space and the solid angles of the pixels in the input image 
# that get mapped to each location in the equirectangular space.
#
# The program is just executed by modifying the code in "__main__".
#
# The user supplies an image (jpg or png) and one or two masks (as .png) with the thought being that
# one could be a lens mask and the other could be a person or lens & person mask. The user
# also supplies the projection type and the distortion parameters as defined in the Agisoft Metashape
# user manual. https://www.agisoft.com/downloads/user-manuals/
#
# The projection types are: "pinhole", "equidistant" or "equisolid". Note that pinhole is
# named "Frame" in Agisoft Metashape.
#
# In the Metashape version 2.3 standard edition manual, the camera models are provided with equations
# in Appendix D.
#
# In writing this code, I supplied the exact equations for the Equisolid lens model initially to
# the AI code that wrote it, later I simply asked AI to find and use the equations for Frame and
# Equidistant projections used by Metashape to extend the functionality.
#
# From the inputs, the code transforms the input image and one or two masks into an Equirectangular
# projection. It also does something else thats pretty cool and informative. It computes the solid
# angle for each pixel from the lens projection and distortion parameters. The solid angle is the
# area of a sphere that a pixel "intersects". The total area of a sphere is 4pi steradians. Thus if
# one adds up the solid angle for all of the pixels in a full 360 equirectangular image the sum
# should be 4pi. The solid angle is also a convenient way to think about resolution (well sampling
# anyway because we are ignoring things like the quality of the optics and motion blur etc). That
# said, you can compute the area of the field of view for a pixel based on the distance from the
# camera. Basically the area is A = SR * r^2  where r is the distance fom the camera (or radius
# of the sphere). In terms of image fidelity, a smaller value of the solid angle is better. For
# a quick "back of the envelope" interpretation the "Ground sample distance" can be thought of as
# the square root of this area. So in addition to the image and mask, the code also computes this
# solid angle and reprojects it to the Equirectangular space. One more thing that is done is
# that the ray directions for the pixels in the output Equirectangular space are computed and
# stored as quaternions.
#
# The output (reprojected image) and one or more reprojected masks are output in jpeg or
# png format. The reprojected solid angle is also computed and stored as a RAW headerless float32
# array of data in raster scan order.
#
# Additionally the output Eqirectangular space is stored in a similar way where we have the
# solid angle for each pixel (for the Equirectangular space itself). Think of this as the capacity
# of this equirectangular image to store data). If the solid angle for a pixel here is larger than
# the remapped solid angle of the input image to this pixel then we cant represent the smaller
# finer resolution of the input image in this 360 ray direction. Image data in the remapping to
# this space would need to be downsampling it. If the equirectangular space solid angle is smaller
# than the remapped input image solid angle then we would be upsampling pixels to store the
# imagery here. Running the code with a larger width for the Equirectangular image will make these
# solid angles smaller because we have more pixels to store the data and sample the sphere more finely.
# The ray directions for the Equirectangular pixels are computed too (4 values in quaternions for each pixel)
# and are stored in a flat, band sequential file in raster scan format. Basically we have
# width x height x 5 floating point values. The first 1/5th of the file stores the solid angles.
# The next 1/5th stores the w component of the ray direction (quaternion). Next is the x, y and z.
# The first value in the file is the upper left pixel, the next is the next pixel in the first
# row of the image. This is a simple raster scan arrangement. There is no header. All of the
# values are stored as float32 format (little endian order on an "Intel PC").
#
# A free program named ImageJ can read these raw binary files if you provide the columns, rows, 
# bands=5 and specify they are float32 (little endian on my computer). ImageJ provides a lot of
# interactive tools for processing the data and doing analysis like plotting line profiles etc.
# If you use this you can File->Import->RAW  (imput Width, Height, Images=5, (little endian on
# a windows PC)
#
# You then need to scale the image (grey levels) to view it. You can do anlysis such as line profiles etc.
#
# Using these tools one could compute thinks like the complete field of view of the lens of a camera
# and the fraction of this field of view that the operator blocks (occludes the environment).
#
# I had a thought that this type of solid angle and ray direction image could be a useful,
# but bulky representation for storing and working with the distortion if it were calculated in
# the original image space. One could directly access the ray direction for any pixel. Distortion
# equations used by different software packages with different equations could all compute these
# ray directions and one could work from there without needing to understand and do n^2
# conversions between different math models. Anyway, here we are are storing these values 
# only for the output Equirectangular space.
#
# Note that I experienced a bug with remapping a frame camera "pinhole" image and see two output
# images and a "halo" surrounding the center image. Maybe someone can fix it?
#
# Good luck!
# And remember that:              !USE AT YOUR OWN RISK!
#
##############################################################################################


import numpy as np
import cv2


# =========================================
# Distortion (forward)
# =========================================
def distort_points(x, y, K1, K2, K3, K4, P1, P2):
    r2 = x*x + y*y
    r4 = r2*r2
    r6 = r4*r2
    r8 = r4*r4

    D = 1 + K1*r2 + K2*r4 + K3*r6 + K4*r8

    dx = P1*(r2 + 2*x*x) + 2*P2*x*y
    dy = P2*(r2 + 2*y*y) + 2*P1*x*y

    xd = x * D + dx
    yd = y * D + dy

    return xd, yd


# =========================================
# Ray → projection (model-specific)
# =========================================
def ray_to_projection(X, Y, Z, model):

    theta = np.arccos(np.clip(Z, -1.0, 1.0))
    phi = np.arctan2(Y, X)

    if model == "pinhole":
        x = X / Z
        y = Y / Z

    elif model == "equidistant":
        r = theta
        x = r * np.cos(phi)
        y = r * np.sin(phi)

    elif model == "equisolid":
        r = 2.0 * np.sin(theta / 2.0)
        x = r * np.cos(phi)
        y = r * np.sin(phi)

    elif model == "equirectangular":
        # Not used here
        raise ValueError("Use direct mapping")

    else:
        raise ValueError("Unknown model")

    return x, y


# =========================================
# Equirectangular rays
# =========================================
def equirectangular_rays(width, height):
    u = np.arange(width)
    v = np.arange(height)
    uu, vv = np.meshgrid(u, v)

    lam = 2*np.pi * (uu / width - 0.5)
    phi = np.pi * (vv / height - 0.5)

    cos_phi = np.cos(phi)

    X = cos_phi * np.sin(lam)
    Y = np.sin(phi)
    Z = cos_phi * np.cos(lam)

    return X, Y, Z, phi

# =========================================
# Distortion inversion (shared)
# =========================================
def undistort_points(xp, yp, K1, K2, K3, K4, P1, P2, iterations=8):
    x = xp.copy()
    y = yp.copy()

    for _ in range(iterations):
        r2 = x*x + y*y
        r4 = r2*r2
        r6 = r4*r2
        r8 = r4*r4

        D = 1 + K1*r2 + K2*r4 + K3*r6 + K4*r8

        dx = P1*(r2 + 2*x*x) + 2*P2*x*y
        dy = P2*(r2 + 2*y*y) + 2*P1*x*y

        x = (xp - dx) / D
        y = (yp - dy) / D

    return x, y
    
# =========================================
# Normalize
# =========================================
def normalize(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


# =========================================
# Projection models
# =========================================
def pinhole_to_rays(x, y):
    return normalize(np.stack([x, y, np.ones_like(x)], axis=-1))


def equidistant_to_rays(x, y):
    r = np.sqrt(x*x + y*y)
    theta = r
    phi = np.arctan2(y, x)

    sin_t = np.sin(theta)

    X = sin_t * np.cos(phi)
    Y = sin_t * np.sin(phi)
    Z = np.cos(theta)

    return np.stack([X, Y, Z], axis=-1)


def equisolid_to_rays(x, y):
    r = np.sqrt(x*x + y*y)
    theta = 2.0 * np.arcsin(np.clip(r/2.0, -1.0, 1.0))
    phi = np.arctan2(y, x)

    sin_t = np.sin(theta)

    X = sin_t * np.cos(phi)
    Y = sin_t * np.sin(phi)
    Z = np.cos(theta)

    return np.stack([X, Y, Z], axis=-1)


def equirectangular_to_rays(width, height):
    u = np.arange(width)
    v = np.arange(height)
    uu, vv = np.meshgrid(u, v)

    lam = 2*np.pi * (uu / width - 0.5)
    phi = np.pi * (vv / height - 0.5)

    cos_phi = np.cos(phi)

    X = cos_phi * np.sin(lam)
    Y = np.sin(phi)
    Z = cos_phi * np.cos(lam)

    rays = np.stack([X, Y, Z], axis=-1)

    return rays, phi
    
def compute_input_solid_angle(width, height, params, model):

    # Reuse your existing ray computation pipeline
    from numpy import gradient, cross, linalg

    f, cx, cy, K1, K2, K3, K4, P1, P2, B1, B2 = params

    u = np.arange(width)
    v = np.arange(height)
    uu, vv = np.meshgrid(u, v)

    up = uu - (width * 0.5 + cx)
    vp = vv - (height * 0.5 + cy)

    yp = vp / f
    xp = (up - B2 * yp) / (f + B1)

    x, y = undistort_points(xp, yp, K1, K2, K3, K4, P1, P2)

    if model == "pinhole":
        rays = pinhole_to_rays(x, y)
    elif model == "equidistant":
        rays = equidistant_to_rays(x, y)
    elif model == "equisolid":
        rays = equisolid_to_rays(x, y)
    else:
        raise ValueError("Unsupported model")

    d_du = np.gradient(rays, axis=1)
    d_dv = np.gradient(rays, axis=0)

    cross_prod = np.cross(d_du, d_dv)
    omega = np.linalg.norm(cross_prod, axis=-1)

    return omega.astype(np.float32)
    
# =========================================
# Main reprojection (FAST)
# =========================================
def reproject_fast(
    image_path,
    model,
    params,
    output_prefix,
    output_width,
    mask1_path=None,
    mask2_path=None
):

    f, cx, cy, K1, K2, K3, K4, P1, P2, B1, B2 = params

    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    h_in, w_in = image.shape[:2]

    mask1 = cv2.imread(mask1_path, cv2.IMREAD_GRAYSCALE) if mask1_path else None
    mask2 = cv2.imread(mask2_path, cv2.IMREAD_GRAYSCALE) if mask2_path else None

    # Output grid
    W_out = output_width
    H_out = output_width // 2

    X, Y, Z, phi_lat = equirectangular_rays(W_out, H_out)

    # =========================================
    # Project rays into input camera
    # =========================================
    x, y = ray_to_projection(X, Y, Z, model)

    # Apply distortion
    xd, yd = distort_points(x, y, K1, K2, K3, K4, P1, P2)

    # Convert to pixel coordinates
    up = xd * (f + B1) + B2 * yd
    vp = yd * f

    u_img = up + (w_in * 0.5 + cx)
    v_img = vp + (h_in * 0.5 + cy)

    map_x = u_img.astype(np.float32)
    map_y = v_img.astype(np.float32)

    # =========================================
    # Resample
    # =========================================
    color_out = cv2.remap(
        image, map_x, map_y,
        interpolation=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT
    )

    if mask1 is not None:
        mask1_out = cv2.remap(mask1, map_x, map_y,
                             interpolation=cv2.INTER_NEAREST)

    if mask2 is not None:
        mask2_out = cv2.remap(mask2, map_x, map_y,
                             interpolation=cv2.INTER_NEAREST)

    # =========================================
    # Compute quaternion directly from rays
    # =========================================
    rays = np.stack([X, Y, Z], axis=-1)

    z_axis = np.array([0, 0, 1.0])
    cross = np.cross(np.broadcast_to(z_axis, rays.shape), rays)
    dot = np.sum(rays * z_axis, axis=-1)

    wq = 1 + dot
    quat = np.concatenate([wq[...,None], cross], axis=-1)

    quat /= np.linalg.norm(quat, axis=-1, keepdims=True)

    # =========================================
    # Solid angle (analytic)
    # =========================================
    dlon = 2*np.pi / W_out
    dlat = np.pi / H_out
    omega = dlon * dlat * np.cos(phi_lat)

    # =========================================
    # Save outputs
    # =========================================
    cv2.imwrite(f"{output_prefix}_color.png", color_out)

    if mask1 is not None:
        cv2.imwrite(f"{output_prefix}_mask1.png", mask1_out)

    if mask2 is not None:
        cv2.imwrite(f"{output_prefix}_mask2.png", mask2_out)

    # RAW BSQ
    data = np.stack([
        omega,
        quat[...,0],
        quat[...,1],
        quat[...,2],
        quat[...,3]
    ], axis=0).astype(np.float32)

    data.tofile(f"{output_prefix}_equirectangular.raw")

    # =========================================
    # Lets reproject the solid angles of the
    # input image from its camera model
    # to the same equirectangular output
    # projection.
    # =========================================
    print("Computing input solid angle map...")
    omega_in = compute_input_solid_angle(w_in, h_in, params, model)

    omega_reprojected = cv2.remap(
    omega_in,
    map_x,
    map_y,
    interpolation=cv2.INTER_NEAREST,
    borderMode=cv2.BORDER_CONSTANT
    )

    # Save reprojected input solid angle image.
    omega_reprojected.astype(np.float32).tofile(f"{output_prefix}_input_solid_angle.raw")

    print("Done.")



    
# =========================================
# Example
# =========================================
if __name__ == "__main__":

    #==========================================================================
    # An equidistant wide angle fisheye example (not superwide).
    # Insta360 OneR 1inch (NOT a spherical camera with this particular lens mod).
    #==========================================================================    
    #width = 5312
    #height = 4912
    #
    #params = (
    #    2300.09046,  # f
    #    48.6187,     # cx
    #    52.6176,     # cy
    #    0.0499776, 0.00096095, -0.00013138, 0.0,  # K1-K4
    #    8.29386e-05, -0.000224424,            # P1, P2
    #    0.0, 0.0             # B1, B2
    #)

    #reproject_fast(
    #    image_path=r"SampleImages\Insta360OneR1inch\IMG_20210522_062640_00_664.jpg",
    #    model="equidistant",
    #    params=params,
    #    output_prefix=r"SampleImages\Insta360OneR1inch\EquirectReprojection",
    #    output_width=7680,
    #    mask1_path=r"SampleImages\Insta360OneR1inch\fullimagemask.png"
    #)

    #==========================================================================
    # An equidistant super wide angle fisheye example.
    # This is from the left camera of a 3Dmakerpro Eagle Max lidar SLAM scanner.
    #==========================================================================    
    #width = 4000
    #height = 3000
    
    #params = (
    #    1129.77431,  # f
    #    -110.626,     # cx
    #    49.7195,     # cy
    #    -0.0434029, 0.00142339, -0.000211098, 0.0,  # K1-K4
    #    -0.000391701, 0.000228375,            # P1, P2
    #    0.0, 0.0             # B1, B2
    #)

    #reproject_fast(
    #    image_path=r"SampleImages\Eagle\1773019342.003189.jpg",
    #    model="equidistant",
    #    params=params,
    #    output_prefix=r"SampleImages\Eagle\EquirectReprojection",
    #    output_width=7680,
    #    mask1_path=r"SampleImages\Eagle\1773019342.003189_mask.png"
    #)
    
    #==========================================================================
    # An high resolution camera with a wide angle lens (frame/rectalinear).
    # This is a Nikon D800 full frame camera with a fixed focal length
    # 20mm f/2.8 lens that is focused at about 2 feet?
    #==========================================================================
    #width = 7360
    #height = 4912

    #params = (
    #    4275.83888,  # f
    #    0.304005,     # cx
    #    -21.5195,     # cy
    #    -0.113624, 0.0944418, -0.0177318, 0.0,  # K1-K4
    #    0.000191501, -0.00059859,            # P1, P2
    #    0.0, 0.0             # B1, B2
    #)

    #reproject_fast(
    #    image_path=r"SampleImages\NikonD80020mm\DSC_4597-Enhanced.jpg",
    #    model="pinhole",
    #    params=params,
    #    output_prefix=r"SampleImages\NikonD80020mm\EquirectReprojection",
    #    output_width=7680,
    #    mask1_path=r"SampleImages\NikonD80020mm\fullmask.png"
    #)
    
    #######################################################################################
# Insta360 X5 - Cam1-Lens0
#    <sensor id="1" label="X5-Cam1-Lens0" type="equisolid_fisheye">
#        <resolution width="3840" height="3840"/>
#        <property name="rolling_shutter" value="true"/>
#        <property name="rolling_shutter_flags" value="63"/>
#        <property name="layer_index" value="0"/>
#        <bands>
#          <band label="Red"/>
#          <band label="Green"/>
#          <band label="Blue"/>
#        </bands>
#        <data_type>uint8</data_type>
#        <calibration type="equisolid_fisheye" class="adjusted">
#          <resolution width="3840" height="3840"/>
#          <f>1038.8800662053641</f>
#          <cx>21.881278610058398</cx>
#          <cy>-7.026678990019831</cy>
#          <k1>0.053306304106176199</k1>
#          <k2>0.044439313326053206</k2>
#          <k3>-0.012265277168873235</k3>
#          <p1>-0.00036101703821687974</p1>
#          <p2>-0.00012934918088242859</p2>
#        </calibration>
#    width = 3840
#    height = 3840
#    params = (
#        1038.8800662053641,  # f
#        21.881278610058398,     # cx
#        -7.026678990019831,     # cy
#        0.053306304106176199, 0.044439313326053206, -0.012265277168873235, 0.0,  # K1-K4
#        -0.00036101703821687974, -0.00012934918088242859,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )

#    reproject_fast(
#        image_path=r"VID_20260407_102313_00_179_lens0_ss412_3fps_0186_86.jpg",
#        model="equisolid",
#        params=params,
#        output_prefix=r"EquirectReprojection_image",
#        output_width=7680,
#        mask1_path=r"VID_20260407_102313_00_179_lens0_ss412_3fps_0186_86.png"
#    )
#    reproject_fast(
#        image_path=r"VID_20260407_102313_00_179_lens0_ss412_3fps_0186_86_imagemaskedge.jpg",
#        model="equisolid",
#        params=params,
#        output_prefix=r"EquirectReprojection_imagemaskedge",
#        output_width=7680,
#        mask1_path=r"VID_20260407_102313_00_179_lens0_ss412_3fps_0186_86.png"
#    )
    
# Insta360 X5 - Cam1-Lens1
#    <sensor id="2" label="X5-Cam1-Lens1" type="equisolid_fisheye">
#        <resolution width="3840" height="3840"/>
#        <property name="rolling_shutter" value="true"/>
#        <property name="rolling_shutter_flags" value="63"/>
#        <property name="layer_index" value="0"/>
#        <bands>
#          <band label="Red"/>
#          <band label="Green"/>
#          <band label="Blue"/>
#        </bands>
#        <data_type>uint8</data_type>
#        <calibration type="equisolid_fisheye" class="adjusted">
#          <resolution width="3840" height="3840"/>
#          <f>1041.8178991493862</f>
#          <cx>7.0646146702966321</cx>
#          <cy>-5.7764831299932045</cy>
#          <k1>0.047511531978151701</k1>
#          <k2>0.048779161586766755</k2>
#          <k3>-0.012979832115337622</k3>
#          <p1>-0.00032466022367088617</p1>
#          <p2>-2.2751621321854161e-05</p2>
#        </calibration>
    width = 3840
    height = 3840
    params = (
        1041.8178991493862,  # f
        7.0646146702966321,     # cx
        -5.7764831299932045,     # cy
        0.047511531978151701, 0.048779161586766755, -0.012979832115337622, 0.0,  # K1-K4
        -0.00032466022367088617, -2.2751621321854161e-05,            # P1, P2
        0.0, 0.0             # B1, B2
    )
    reproject_fast(
        image_path=r"VID_20260407_102313_00_179_lens1_ss412_3fps_0186_186.jpg",
        model="equisolid",
        params=params,
        output_prefix=r"EquirectReprojection_image",
        output_width=7680,
        mask1_path=r"VID_20260407_102313_00_179_lens1_ss412_3fps_0186_186.png"
    )
    reproject_fast(
        image_path=r"VID_20260407_102313_00_179_lens1_ss412_3fps_0186_186_imagemaskedge.jpg",
        model="equisolid",
        params=params,
        output_prefix=r"EquirectReprojection_imagemaskedge",
        output_width=7680,
        mask1_path=r"VID_20260407_102313_00_179_lens1_ss412_3fps_0186_186.png"
    )
    
# Insta360 X5 - Cam2-Lens3
#    <sensor id="3" label="X5-Cam2-Lens3" type="equisolid_fisheye">
#        <resolution width="3840" height="3840"/>
#        <property name="rolling_shutter" value="true"/>
#        <property name="rolling_shutter_flags" value="63"/>
#        <property name="layer_index" value="0"/>
#        <bands>
#          <band label="Red"/>
#          <band label="Green"/>
#          <band label="Blue"/>
#        </bands>
#        <data_type>uint8</data_type>
#        <calibration type="equisolid_fisheye" class="adjusted">
#          <resolution width="3840" height="3840"/>
#          <f>1037.0588885005184</f>
#          <cx>21.741111598240604</cx>
#          <cy>-17.016316430140083</cy>
#          <k1>0.04985676153696534</k1>
#          <k2>0.046716530545904203</k2>
#          <k3>-0.012712543993973272</k3>
#          <p1>0.002540015983952868</p1>
#          <p2>-0.0010087564830385536</p2>
#        </calibration>
#    width = 3840
#    height = 3840
#    params = (
#        1037.0588885005184,  # f
#        21.741111598240604,     # cx
#        -17.016316430140083,     # cy
#        0.04985676153696534, 0.046716530545904203, -0.012712543993973272, 0.0,  # K1-K4
#        0.002540015983952868, -0.0010087564830385536,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )
#    generate_camera_data(width, height, params, model="equisolid")
# Insta360 X5 - Cam2-Lens4
#    <sensor id="4" label="X5-Cam2-Lens4" type="equisolid_fisheye">
#        <resolution width="3840" height="3840"/>
#        <property name="rolling_shutter" value="true"/>
#        <property name="rolling_shutter_flags" value="63"/>
#        <property name="layer_index" value="0"/>
#        <bands>
#          <band label="Red"/>
#          <band label="Green"/>
#          <band label="Blue"/>
#        </bands>
#        <data_type>uint8</data_type>
#        <calibration type="equisolid_fisheye" class="adjusted">
#          <resolution width="3840" height="3840"/>
#          <f>1034.4967439597292</f>
#          <cx>2.2694357723285226</cx>
#          <cy>6.3906460294022915</cy>
#          <k1>0.055325342381608945</k1>
#          <k2>0.038875523239894932</k2>
#          <k3>-0.0099718952583186336</k3>
#          <p1>0.00065208578033726101</p1>
#          <p2>-5.1004565602410307e-05</p2>
#        </calibration>
#    width = 3840
#    height = 3840
#    params = (
#        1034.4967439597292,  # f
#        2.2694357723285226,     # cx
#        6.3906460294022915,     # cy
#        0.055325342381608945, 0.038875523239894932, -0.0099718952583186336, 0.0,  # K1-K4
#        0.00065208578033726101, -5.1004565602410307e-05,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )
#    generate_camera_data(width, height, params, model="equisolid")
#######################################################################################
    
    