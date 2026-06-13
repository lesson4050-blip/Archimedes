import cv2
import numpy as np

def trace_to_svg(image_path, output_svg_path, y_min=0, y_max=None, is_white=False, is_square=False):
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image from {image_path}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # If y_max is not specified, use the full height
    if y_max is None:
        y_max = gray.shape[0]
        
    # Crop the image to the specified y range
    cropped = gray[y_min:y_max, :]
    
    # Threshold the image: background is white (255), foreground is dark (< 240)
    # We want foreground to be white (255) and background black (0) for findContours
    _, thresh = cv2.threshold(cropped, 240, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours
    # cv2.RETR_LIST retrieves all contours without hierarchy
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_L1)
    
    # Filter out very small noise contours (e.g. less than 5 pixels in area)
    valid_contours = [c for c in contours if cv2.contourArea(c) > 5]
    
    if not valid_contours:
        raise ValueError("No contours found in the specified range")
        
    all_pts = np.vstack(valid_contours)
    x_min_c = int(np.min(all_pts[:, 0, 0]))
    x_max_c = int(np.max(all_pts[:, 0, 0]))
    y_min_c = int(np.min(all_pts[:, 0, 1]))
    y_max_c = int(np.max(all_pts[:, 0, 1]))
    
    width = x_max_c - x_min_c + 1
    height = y_max_c - y_min_c + 1
    
    # Determine padding and viewport sizing
    if is_square:
        # Make the viewport square to fit circular/square icon grids
        max_dim = max(width, height)
        # Use 15% padding of the max dimension
        pad = int(max_dim * 0.15)
        view_w = max_dim + 2 * pad
        view_h = max_dim + 2 * pad
        # Center the content within the square viewport
        off_x = pad + (max_dim - width) // 2 - x_min_c
        off_y = pad + (max_dim - height) // 2 - y_min_c
    else:
        # Standard rectangular layout with 10% padding
        pad_x = int(width * 0.1)
        pad_y = int(height * 0.1)
        view_w = width + 2 * pad_x
        view_h = height + 2 * pad_y
        off_x = pad_x - x_min_c
        off_y = pad_y - y_min_c
        
    path_data = []
    for c in valid_contours:
        # Simplify the contour points to make SVG clean and smooth
        epsilon = 0.6
        approx = cv2.approxPolyDP(c, epsilon, closed=True)
        
        points = approx[:, 0, :]
        if len(points) < 3:
            continue
            
        # Write path segment
        seg = f"M {points[0][0] + off_x},{points[0][1] + off_y}"
        for pt in points[1:]:
            seg += f" L {pt[0] + off_x},{pt[1] + off_y}"
        seg += " Z"
        path_data.append(seg)
        
    path_str = " ".join(path_data)
    
    # SVG color configuration
    fill_color = "#FFFFFF" if is_white else "#000000"
    
    # Generate SVG content
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_w} {view_h}" width="{view_w}" height="{view_h}">\n'
    svg += f'  <path d="{path_str}" fill="{fill_color}" fill-rule="evenodd"/>\n'
    svg += '</svg>\n'
    
    with open(output_svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
        
    print(f"Successfully traced and wrote {output_svg_path} (viewbox: {view_w}x{view_h})")

if __name__ == "__main__":
    # 1. Full logo (icon + text) - aspect ratio natural
    trace_to_svg("assets/logos/master-logo.png", "assets/logos/logo-full.svg", y_min=0, y_max=None, is_white=False, is_square=False)
    trace_to_svg("assets/logos/master-logo.png", "assets/logos/logo-full-white.svg", y_min=0, y_max=None, is_white=True, is_square=False)
    
    # 2. Icon only (DNA helix) - square aspect ratio for favicons and app icons
    trace_to_svg("assets/logos/master-logo.png", "assets/logos/logo-icon.svg", y_min=0, y_max=610, is_white=False, is_square=True)
    trace_to_svg("assets/logos/master-logo.png", "assets/logos/logo-icon-white.svg", y_min=0, y_max=610, is_white=True, is_square=True)
