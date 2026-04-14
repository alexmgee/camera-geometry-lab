import cv2
import numpy as np
import argparse

def main():
    # 1. Set up command line arguments
    parser = argparse.ArgumentParser(description='Overlay mask boundaries on a color image.')
    parser.add_argument('mask_path', help='Path to the mask image (0 = invalid, >0 = valid)')
    parser.add_argument('image_path', help='Path to the color image')
    parser.add_argument('output_path', help='Path to save the output image')
    args = parser.parse_args()

    # 2. Load images
    # Mask is loaded as grayscale, image is loaded as color (BGR)
    mask = cv2.imread(args.mask_path, cv2.IMREAD_GRAYSCALE)
    img = cv2.imread(args.image_path)

    if mask is None or img is None:
        print("Error: Could not load one or both images. Check your file paths.")
        return

    # 3. Validation
    if mask.shape[:2] != img.shape[:2]:
        print("Error: Mask and Image dimensions do not match.")
        return

    # 4. Process the mask
    # Convert all non-zero values to 255 to create a clean binary mask
    _, binary_mask = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY)

    # Use dilation to find the boundary. This is functionally equivalent 
    # to checking if a 3x3 neighborhood around an invalid pixel contains a valid one.
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(binary_mask, kernel, iterations=1)
    
    # The boundary is where the dilated mask is 'valid' but the original was 'invalid'
    boundary = cv2.absdiff(dilated, binary_mask)

    # 5. Overlay and Save
    # Apply white (255, 255, 255) to the color image where the boundary exists
    img[boundary > 0] = [255, 255, 255]

    cv2.imwrite(args.output_path, img)
    print(f"Successfully saved boundary overlay to: {args.output_path}")

if __name__ == "__main__":
    main()
