import numpy as np
import cv2
from scipy.optimize import minimize
import os

def process_camera_calibration(input_bin, mask_png, width, height, output_raw, theta_png, phi_png):
    # 1. Read binary data (5 bands, Little Endian Float32)
    # Band order: Solid Angle, Qw, Qx, Qy, Qz
    if not os.path.exists(input_bin):
        print(f"Error: {input_bin} not found.")
        return
    
    data = np.fromfile(input_bin, dtype='<f4')
    if data.size != 5 * width * height:
        print(f"Error: Expected {5 * width * height} elements, got {data.size}.")
        return
    
    bands = data.reshape(5, height, width)
    # Skip Band 0 (Solid Angle), take quaternions
    qw, qx, qy, qz = bands[1], bands[2], bands[3], bands[4]

    # 2. Load Validity Mask
    # Mask value 0 = invalid, anything else = valid
    if os.path.exists(mask_png):
        mask = cv2.imread(mask_png, cv2.IMREAD_GRAYSCALE)
        if mask.shape != (height, width):
            mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
        valid_mask = mask > 0
    else:
        print("Warning: Mask file not found. Processing all pixels.")
        valid_mask = np.ones((height, width), dtype=bool)

    # 3. Convert Quaternions to Local Ray Vectors (Z-forward convention)
    vx = 2 * (qx * qz + qw * qy)
    vy = 2 * (qy * qz - qw * qx)
    vz = 1 - 2 * (qx**2 + qy**2)

    # 4. Calculate Polar Coordinates
    theta_rad = np.arccos(np.clip(vz, -1.0, 1.0))
    phi_rad = np.arctan2(vy, vx)
    
    theta_deg = np.degrees(theta_rad)
    phi_deg = np.degrees(phi_rad)

    # Apply mask: Set invalid areas to 0
    theta_deg_masked = np.where(valid_mask, theta_deg, 0)
    phi_deg_masked = np.where(valid_mask, phi_deg, 0)

    # 5. Save to 2-band RAW float32 (Little Endian)
    raw_output = np.stack([theta_deg_masked, phi_deg_masked], axis=0).astype('<f4')
    raw_output.tofile(output_raw)

    # 6. Create PNG Visualizations
    # Theta: Clipped 0-255
    theta_vis = np.clip(theta_deg_masked, 0, 255).astype(np.uint8)
    
    # Phi: Scale [-255, 255] to [0, 255] and force mask black
    phi_scaled = (phi_deg_masked + 255) / 2.0
    phi_vis = np.clip(phi_scaled, 0, 255).astype(np.uint8)
    phi_vis[~valid_mask] = 0 # Ensure masked pixels are pure black
    
    cv2.imwrite(theta_png, theta_vis)
    cv2.imwrite(phi_png, phi_vis)

    # 7. Optimization for COLMAP Parameters
    # Use only valid pixels to perform the fit
    v_idx, u_idx = np.indices((height, width))
    u_target = u_idx[valid_mask].flatten()
    v_target = v_idx[valid_mask].flatten()
    th_val = theta_rad[valid_mask].flatten()
    ph_val = phi_rad[valid_mask].flatten()
    
    # Subsample to speed up optimization if dataset is very large
    if len(th_val) > 20000:
        sample_idx = np.random.choice(len(th_val), 20000, replace=False)
        u_target, v_target = u_target[sample_idx], v_target[sample_idx]
        th_val, ph_val = th_val[sample_idx], ph_val[sample_idx]

    def colmap_residual(p):
        fx, fy, cx, cy, k1, k2, k3, k4, p1, p2, s1, s2 = p
        # Radial projection component
        r_th = th_val + k1*th_val**3 + k2*th_val**5 + k3*th_val**7 + k4*th_val**9
        xh, yh = r_th * np.cos(ph_val), r_th * np.sin(ph_val)
        
        # Tangential and Thin-Prism distortion
        r2 = xh**2 + yh**2
        du = p1*(r2 + 2*xh**2) + 2*p2*xh*yh + s1*r2
        dv = p2*(r2 + 2*yh**2) + 2*p1*xh*yh + s2*r2
        
        u_pred = fx * (xh + du) + cx
        v_pred = fy * (yh + dv) + cy
        return np.mean((u_pred - u_target)**2 + (v_pred - v_target)**2)

    # Initial Guess (Center of frame, width as focal length)
    p_initial = [width, width, width/2, height/2, 0, 0, 0, 0, 0, 0, 0, 0]
    res = minimize(colmap_residual, p_initial, method='L-BFGS-B')
    
    print("\nFit Complete. THIN_PRISM_FISHEYE Parameters:")
    print(" ".join(map(str, res.x)))
    return res.x

# --- Configuration ---
# Width, Height = 3000, 4000
process_camera_calibration(r"camera_equisolid_3840x3840_344f216a.raw", r"Colmap_Equisolid\VID_20260407_102227_00_120_lens4_ss412_3fps_0195_395.png", 3840, 3840, 'rays_RAWfloat32_POLARANGLE_and_AZIMUTH.raw', 'POLARANGLE_theta.png', 'AZIMUTH_phi_scaled.png')

