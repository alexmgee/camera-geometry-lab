##############################################################################################
#
# Program: Convert_CalibratedFrameEquidistantEquisolidEquirectangularModel_to_SolidAngle_and_RayDirections.py
# Author: Mike Heath  (but mostly AI)
# Date: 4/4/2026
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
# My goal here was to set up a universal framework to work within that is "convenient"
# regarding cameras and camera calibrations. In my understanding, there are many different
# conventions for storing camera calibrations that may be inconsistent with eachother. It is
# also inconvenient to work with a camera model with distortion parameters because the process
# of determining the effective "ray direction" for each pixel is cumbersome, usually involving
# some type of iterative computational solution (because the equations are not generally
# invertible in closed form).
#
# Here I've tried, and I hope it works, to compute the solid angle of each pixel in an image
# and the ray direction (as a quaternion). This is just another format to store and represent
# the image intrinsics.
#
# The parameterization I've used here is based on my (and heavily on AI's) understanding of
# the conventions used in Agisoft Metashape and how to transform a calibration to this new
# format.
#
# It will be POSSIBLE to convert lens calibrations in other conventions to this format too
# such as those from Reality Scan though I have not done that yet.
#
# It seems to me that working with quaternions SHOULD be convenient for transforming these
# camera ray directions using the extrinsics for an "aligned" set of images.
#
# My first use of this program will be to look at conversions from equisolid "dual-fisheye"
# 360 camera data into either equirectangular and then into cube map format. These are not
# implemented in this code, but will use the solid angle and ray direction calculations implemented 
# here. I think it will be interesting to follow what happens to the solid angles in different ray
# directions through these processing chains. Of course any conversion from dual fisheyes to an
# equirectanguler (without the nodal points aligned) is a mashing of the data together
# because the ray directions of the fisheye images will NOT be compatible for both fisheye images.
# Thus, while converting dual equisolid fisheye images to equirectangular (and then cubemap)
# offers "convenient canned solutions" and workflows today, it is NOT the correct approach.
# I believe that one day when the tools are in place to train GS on equisolid fisheye
# images, people will understand this.
#
# Later, I hope to consider an equisolid to equidistant image conversion (throwing away data
# beyond 180 degrees). That would be one way to train Gaussian Splats using implementations
# of GUT that exist today. I also hope to consider an equisolid to multiple pinhole conversion
# say to convert one fisheye image into into either five faces of a cube or to six faces of
# a dodecahedron (but extending five of the six faces to handle more field of view. Will
# that work and work well? I don't yet know.
#
# Anyway.... Just throwing this out there for other folks to use if they want.
#
# This program outputs "RAW Band sequential files in float32 format". Each of the images
# are stored in raster order one following the next. They are:
#
#   First: Solid angle in steradians
#   Next: the Quaternions (four images (w,x,y,z)).
#
# One can use whatever program one desires to view/inspect the output images.
# 
# One option is ImageJ (which can be found on-line and downloaded for free).
#
# If you use this you can File->Import->RAW  (imput Width, Height, Images=5, little endian on a windows PC)
#
# You then need to scale the image to view it (its float32). You can do anlysis such as line
# profiles etc.
#
# Good luck!
#
# And remember that:              !USE AT YOUR OWN RISK!
#
##############################################################################################

import numpy as np
import hashlib


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


# =========================================
# Ray → quaternion
# =========================================
def rays_to_quaternion(rays):
    z = np.array([0.0, 0.0, 1.0])

    cross = np.cross(np.broadcast_to(z, rays.shape), rays)
    dot = np.sum(rays * z, axis=-1)

    w = 1.0 + dot
    xyz = cross

    quat = np.concatenate([w[...,None], xyz], axis=-1)

    norm = np.linalg.norm(quat, axis=-1, keepdims=True)
    quat /= np.maximum(norm, 1e-12)

    return quat


# =========================================
# Solid angle (finite diff)
# =========================================
def compute_solid_angle_fd(rays):
    d_du = np.gradient(rays, axis=1)
    d_dv = np.gradient(rays, axis=0)
    cross = np.cross(d_du, d_dv)
    return np.linalg.norm(cross, axis=-1)


# =========================================
# Build rays
# =========================================
def compute_rays(width, height, params, model):

    if model == "equirectangular":
        rays, phi = equirectangular_to_rays(width, height)
        return rays, phi

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
        raise ValueError("Unknown model")

    return rays, None


# =========================================
# Filename
# =========================================
def generate_filename(width, height, params, model):
    param_str = model + "_" + "_".join([f"{p:.6g}" for p in params])
    h = hashlib.md5(param_str.encode()).hexdigest()[:8]
    return f"camera_{model}_{width}x{height}_{h}.raw"


# =========================================
# Main
# =========================================
def generate_camera_data(width, height, params, model):

    print(f"Model: {model}")
    rays, phi = compute_rays(width, height, params, model)

    print("Computing solid angle...")

    if model == "equirectangular":
        dlon = 2*np.pi / width
        dlat = np.pi / height
        omega = dlon * dlat * np.cos(phi)
    else:
        omega = compute_solid_angle_fd(rays)

    print("Computing quaternions...")
    quat = rays_to_quaternion(rays)

    filename = generate_filename(width, height, params, model)

    print(f"Writing {filename}...")

    data = np.stack([
        omega,
        quat[...,0],
        quat[...,1],
        quat[...,2],
        quat[...,3]
    ], axis=0).astype(np.float32)

    data.tofile(filename)

    print("Done.")
    return filename


# =========================================
# Example usage
# =========================================
if __name__ == "__main__":

######################################################################################
# Equirectangular References:
#
#   Has a width to height ratio of 2:1 and the focal length is irrelevant, also
#   distortion should have been removed in its creation.
#
#       8k                          =   7680 x 3840
#       5.7k                        =   5760 x 2880
#       Old Ricoh Theta S (photo)   =   5376 x 2688
#
#       Width: 7680
#       Height: 3840
#       f: 1.0            # irrelevant
#       cx: 0.0
#       cy: 0.0
#       k1: 0.0
#       k2: 0.0
#       k3: 0.0
#       k4: 0.0
#       p1: 0.0
#       p2: 0.0
#       b1: 0.0
#       b2: 0.0
#
#    params = (
#        1.0,  # f
#        0.0,     # cx
#        0.0,     # cy
#        0.0, 0.0, 0.0, 0.0,  # K1-K4
#        0.0, 0.0,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )
#
#    generate_camera_data(width, height, params, model="pinhole")
#
######################################################################################
#
# Pinhole (Frame) References:
#
#
#   Cubemap: The focal length is 1/2 of the images height, and the height is equal to the width. 
#   There are no distortion coefficients.
#
#       The solid angle has a maximum at the center (optical axis). The solid angle (resolution)
#       gets better as the ray direction goes towards the edges and corners of the cube (since
#       it is a frame/pinhole projection).
#       This is a simple camera model. The solid angle of the central pixel (on the
#       optical axis) can be computed as:
#
#           CentralPixel_SA = 4*arctan(1/(w*sqrt(w*w+2)))   , w is the image width & height
#
#           w = sqrt(csc(SA / 4) - 1)
#
#       Thus an "ideal" 8k Equisolid Equirectangular image (SA=6.69325402e-7 on the middle row)
#       would need a pinhole cube face image of 2444.62 pixel width and height to match the solid
#       angle (resolution) in that direction. I think a lot of people may use 1920x1920 cube map
#       faces 
#
#
#       Width: 2446
#       Height: 2446
#       f: 960.0
#       cx: 0.0
#       cy: 0.0
#       k1: 0.0
#       k2: 0.0
#       k3: 0.0
#       k4: 0.0
#       p1: 0.0
#       p2: 0.0
#       b1: 0.0
#       b2: 0.0
#
#    width = 2446
#    height = 2446
#
#    params = (
#        1223.0,  # f
#        0.0,     # cx
#        0.0,     # cy
#        0.0, 0.0, 0.0, 0.0,  # K1-K4
#        0.0, 0.0,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )
#    generate_camera_data(width, height, params, model="pinhole")
#
#
#
#
#   Frame: Nikon D800 w/20mm f/2.8 fixed (no zoom - focused close and unchanged for capture)
#
#       Width: 7360
#       Height: 4912
#       f: 4275.83888
#       cx: 0.304005
#       cy: -21.5195
#       k1: -0.113624
#       k2: 0.0944418
#       k3: -0.0177318
#       k4: 0.0
#       p1: 0.000191501
#       p2: -0.00059859
#       b1: 0.0
#       b2: 0.0
#
#    width = 7360
#    height = 4912
#
#    params = (
#        4275.83888,  # f
#        0.304005,     # cx
#        -21.5195,     # cy
#        -0.113624, 0.0944418, -0.0177318, 0.0,  # K1-K4
#        0.000191501, -0.00059859,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )
#    generate_camera_data(width, height, params, model="pinhole")
#
######################################################################################
#
# Fisheye Equidistant References:
#
#   Insta360 OneR 1 inch PHOTO (not a 360 camera!)
#
#       Width: 5312
#       Height: 3553
#       f: 2300.09046
#       cx: 48.6187
#       cy: 52.6176
#       k1: 0.0499776
#       k2: 0.00096095
#       k3: -0.00013138
#       k4: 0.0
#       p1: 8.29386e-05
#       p2: -0.000224424
#       b1: 0.0
#       b2: 0.0
#
#    width = 5312
#    height = 4912
#
#    params = (
#        2300.09046,  # f
#        48.6187,     # cx
#        52.6176,     # cy
#        0.0499776, 0.00096095, -0.00013138, 0.0,  # K1-K4
#        8.29386e-05, -0.000224424,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )
#    generate_camera_data(width, height, params, model="equidistant")
#
#######################################################################################
#
# Fisheye Equisolid References:
#
# I need some data! Most modern 360 (spherical cameras) use two equisolid lenses.
#
#    This is data from a Raven scanner.
#
#    "LEFT LENS"
#    <calibration type="equisolid_fisheye" class="adjusted">
#          <resolution width="4000" height="3000"/>
#          <f>1126.2091884624315</f>
#          <cx>-64.799331342266001</cx>
#          <cy>-18.199377487420378</cy>
#          <k1>-0.00096001933702607903</k1>
#          <k2>0.0020315363607052808</k2>
#          <k3>-0.00077599827289428472</k3>
#          <p1>-4.007152494093011e-05</p1>
#          <p2>-7.656283216647622e-05</p2>
#        </calibration>
#        <black_level>0 0 0</black_level>
#        <sensitivity>1 1 1</sensitivity>
#        <meta>
#
#    width = 4000
#    height = 3000
#    params = (
#        1126.2091884624315,  # f
#        -64.799331342266001,     # cx
#        -18.199377487420378,     # cy
#        -0.00096001933702607903, 0.0020315363607052808, -0.00077599827289428472, 0.0,  # K1-K4
#        -4.007152494093011e-05, -7.656283216647622e-05,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )
#    generate_camera_data(width, height, params, model="equisolid")
#
#          <property name="Exif/Make" value="3DMakerPro"/>
#          <property name="Exif/Model" value="Raven-Left"/>
#        </meta>
#      </sensor>
#      <sensor id="1" label="Raven-Right" type="equisolid_fisheye">
#        <resolution width="4000" height="3000"/>
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
#          <resolution width="4000" height="3000"/>
#          <f>1126.0161233652082</f>
#          <cx>48.111512364194176</cx>
#          <cy>70.987574132578843</cy>
#          <k1>0.00010310036615239277</k1>
#          <k2>0.0011064393552231945</k2>
#          <k3>-0.00045740565756664781</k3>
#          <p1>-0.00010476941226443689</p1>
#          <p2>0.00030064236485620753</p2>
#        </calibration>
#        <black_level>0 0 0</black_level>
#        <sensitivity>1 1 1</sensitivity>
#
#    width = 4000
#    height = 3000
#    params = (
#        1126.0161233652082,  # f
#        48.111512364194176,     # cx
#        70.987574132578843,     # cy
#        0.00010310036615239277, 0.0011064393552231945, -0.00045740565756664781, 0.0,  # K1-K4
#        -0.00010476941226443689, 0.00030064236485620753,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )
#    generate_camera_data(width, height, params, model="equisolid")
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
#    generate_camera_data(width, height, params, model="equisolid")
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
#    width = 3840
#    height = 3840
#    params = (
#        1041.8178991493862,  # f
#        7.0646146702966321,     # cx
#        -5.7764831299932045,     # cy
#        0.047511531978151701, 0.048779161586766755, -0.012979832115337622, 0.0,  # K1-K4
#        -0.00032466022367088617, -2.2751621321854161e-05,            # P1, P2
#        0.0, 0.0             # B1, B2
#    )
#    generate_camera_data(width, height, params, model="equisolid")
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
    width = 3840
    height = 3840
    params = (
        1034.4967439597292,  # f
        2.2694357723285226,     # cx
        6.3906460294022915,     # cy
        0.055325342381608945, 0.038875523239894932, -0.0099718952583186336, 0.0,  # K1-K4
        0.00065208578033726101, -5.1004565602410307e-05,            # P1, P2
        0.0, 0.0             # B1, B2
    )
    generate_camera_data(width, height, params, model="equisolid")
#######################################################################################
