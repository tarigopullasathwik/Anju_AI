import os

def take_picture(filename: str = "capture.jpg"):
    """
    Captures a single frame from the default webcam and saves it.
    """
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Error: Could not access the webcam."

        # Give some time to warm up
        for _ in range(10):
            ret, frame = cap.read()

        if ret:
            output_path = os.path.abspath(filename)
            cv2.imwrite(output_path, frame)
            cap.release()
            return output_path
        else:
            cap.release()
            return "Error: Failed to capture image from webcam."
    except Exception as e:
        return f"Error in camera tool: {e}"
