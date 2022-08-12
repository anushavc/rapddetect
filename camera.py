# Let us import the Libraries required.
import cv2
import numpy as np


class VideoCamera(object):

    """ Takes the Real time Video, Predicts the Emotion using pre-trained model. """
    def __init__(self):
        self.video = cv2.VideoCapture(0)

    def __del__(self):
        self.video.release()

    def get_frame(self):
        # Reading the Video and grasping the Frames
        _, frame = self.video.read()

        # Converting the Color image to Gray Scale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Encoding the Image into a memory buffer
        _, jpeg = cv2.imencode('.jpg', frame)

        # Returning the image as a bytes object
        return jpeg.tobytes()
