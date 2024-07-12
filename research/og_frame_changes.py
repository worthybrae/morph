'''start = time.time()
    # Edge detection
    edges = cv2.Canny(gray, 400, 450, apertureSize=5)
    times['edge_detection'] = time.time() - start

    output_filename = 'tmp/hls/edges.png'
    cv2.imwrite(output_filename, edges)

    start = time.time()
    # Contour detection and smoothing
    contours, _ = cv2.findContours(edges.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    smoothed_contours = [smooth_contour(contour) for contour in contours]
    edge_drawing = np.zeros(gray.shape, dtype=np.uint8)
    cv2.drawContours(edge_drawing, smoothed_contours, -1, (255, 255, 255), 1)
    times['contour_smoothing'] = time.time() - start

    start = time.time()
    # Convert edge_drawing to float and normalize to range [0, 1]
    edges_normalized = edge_drawing.astype(float) / 255.0
    # Expand dimensions to match the shape of color arrays
    edges_normalized = edges_normalized[:, :, np.newaxis]
    times['normEdges'] = time.time() - start

    start = time.time()
    matrix_3d = np.full((height, width, 3), background_color, dtype=np.uint8)
    background = (edges * line_color + (1 - edges) * background_color).astype(frame.dtype)
    times['create_background'] = time.time() - start'''