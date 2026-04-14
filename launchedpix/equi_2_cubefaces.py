import numpy as np
import cv2
import glob
import os
from tqdm import tqdm

# =========================
# CONFIG
# =========================
#RAW_FILE   = "camera_equisolid_3840x3840_5054369d.raw"
RAW_FILE   = "camera_equisolid_3840x3840_64105872.raw"
COLOR_GLOB = "images/*.jpg"
MASK_GLOB  = "masks/*.png"
OUTPUT_DIR = "output"
N = 1920                  # final cube face size
PAD = 10                 # extra border
F = N / 2.0              # focal length

# =========================
# LOAD BAND-SEQUENTIAL
# =========================
def load_bs(filename):
    data = np.fromfile(filename, dtype=np.float32)
    bands = 5

    #pixels = data.size // bands
    #H = int(np.sqrt(pixels / 2))
    #W = 2 * H

    H = 3840
    W = 3840
	
    data = data.reshape((bands, H, W))
    return data, H, W

# =========================
# QUAT → RAY
# =========================
def quat_to_ray(qw, qx, qy, qz):
    x = 2*(qx*qz + qw*qy)
    y = 2*(qy*qz - qw*qx)
    z = 1 - 2*(qx*qx + qy*qy)

    rays = np.stack([x, y, z], axis=-1)
    norms = np.linalg.norm(rays, axis=-1, keepdims=True)
    return rays / norms

# =========================
# FACE INTERSECTION
# =========================
def project_to_face(ray, face):
    x, y, z = ray

    if face == "+Z" and z > 0:
        u = x / z
        v = y / z
    elif face == "+X" and x > 0:
        u = -z / x
        v = y / x
    elif face == "-X" and x < 0:
        u = z / -x
        v = y / -x
    elif face == "+Y" and y > 0:
        u = x / y
        v = -z / y
    elif face == "-Y" and y < 0:
        u = x / -y
        v = z / -y
    else:
        return None

    return u, v

# =========================
# SPLAT (BILINEAR)
# =========================
def splat(buffer, weight, u, v, value):
    H, W = buffer.shape[:2]

    x = u
    y = v

    x0 = int(np.floor(x))
    y0 = int(np.floor(y))
    dx = x - x0
    dy = y - y0

    for iy in [0, 1]:
        for ix in [0, 1]:
            xx = x0 + ix
            yy = y0 + iy

            if 0 <= xx < W and 0 <= yy < H:
                w = (1 - abs(ix - dx)) * (1 - abs(iy - dy))
                buffer[yy, xx] += value * w
                weight[yy, xx] += w

# =========================
# PROCESS ONE IMAGE
# =========================
def process_image(rays, img, mask, faces):
    Hs, Ws, _ = rays.shape

    size = N + PAD
    center = size // 2

    outputs = {}

    for face in faces:
        buf_img = np.zeros((size, size, 3), dtype=np.float32)
        buf_w   = np.zeros((size, size), dtype=np.float32)

        buf_mask = np.zeros((size, size), dtype=np.float32)
        buf_mw   = np.zeros((size, size), dtype=np.float32)

        print(f"Splatting face {face}")

        for y in tqdm(range(Hs)):
            for x in range(Ws):
                if mask[y, x] == 0:
                    continue

                ray = rays[y, x]
                proj = project_to_face(ray, face)
                if proj is None:
                    continue

                u, v = proj

                px = u * F + center
                py = v * F + center

                splat(buf_img, buf_w, px, py, img[y, x].astype(np.float32))
                splat(buf_mask, buf_mw, px, py, float(mask[y, x]))

        # normalize
        valid = buf_w > 0
        buf_img[valid] /= buf_w[valid][:, None]

        valid_m = buf_mw > 0
        buf_mask[valid_m] /= buf_mw[valid_m]

        # threshold mask
        buf_mask = (buf_mask > 127).astype(np.uint8) * 255

        # crop center
        start = (size - N) // 2
        end = start + N

        outputs[face] = (
            buf_img[start:end, start:end].astype(np.uint8),
            buf_mask[start:end, start:end]
        )

    return outputs

# =========================
# MAIN
# =========================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    data, H, W = load_bs(RAW_FILE)
    qw, qx, qy, qz = data[1], data[2], data[3], data[4]

    print("Computing rays...")
    rays = quat_to_ray(qw, qx, qy, qz)

    faces = ["+Z", "+X", "-X", "+Y", "-Y"]

    color_files = sorted(glob.glob(COLOR_GLOB))
    mask_files  = sorted(glob.glob(MASK_GLOB))

    for cfile, mfile in zip(color_files, mask_files):
        print(f"Processing {cfile}")

        img  = cv2.imread(cfile)
        mask = cv2.imread(mfile, cv2.IMREAD_GRAYSCALE)

        outputs = process_image(rays, img, mask, faces)

        base = os.path.splitext(os.path.basename(cfile))[0]

        for face in faces:
            out_img, out_mask = outputs[face]

            cv2.imwrite(f"{OUTPUT_DIR}/{base}_{face}.jpg", out_img)
            cv2.imwrite(f"{OUTPUT_DIR}/{base}_{face}_mask.png", out_mask)

    print("Done!")

if __name__ == "__main__":
    main()