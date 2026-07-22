
import cv2
import numpy as np
import os

print("Attempting to create an OpenCV window...")
try:
    # Create a simple black image
    img = np.zeros((200, 400, 3), dtype=np.uint8)
    cv2.putText(img, "X11 Window Test", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    cv2.namedWindow("Test Window")
    cv2.imshow("Test Window", img)
    print("Window created successfully! Press any key in the window to close.")
    cv2.waitKey(1) # Give it a moment to render
    cv2.destroyAllWindows()
    print("Window closed successfully.")
except Exception as e:
    print(f"Failed to create window: {e}")
