import sys
import cv2
import numpy as np
import math
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtOpenGL import QGLWidget
from PyQt5.QtCore import Qt, QTimer
from OpenGL.GL import *
from OpenGL.GLU import *


class PanoramaViewer(QGLWidget):
    def __init__(self, image_path):
        super().__init__()

        # REQUIRED for keyboard input
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        self.image_path = image_path

        # Camera orientation
        self.yaw = 0.0
        self.pitch = 0.0
        self.fov = 100.0  # ~15mm lens feel

        # Camera position
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.cam_z = 0.0

        self.last_x = 0
        self.last_y = 0

        self.texture_id = None
        self.keys = set()

        # Movement loop (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_movement)
        self.timer.start(16)

    # ---------------- OPENGL ---------------- #

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        glClearColor(0, 0, 0, 1)

        self.texture_id = glGenTextures(1)
        self.load_texture()

    def load_texture(self):
        img = cv2.imread(
            self.image_path,
            cv2.IMREAD_ANYDEPTH | cv2.IMREAD_COLOR
        )

        if img is None:
            raise RuntimeError("Failed to load image")

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if img.dtype != np.uint8:
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
            img = img.astype(np.uint8)

        h, w, _ = img.shape

        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGB,
            w, h, 0, GL_RGB,
            GL_UNSIGNED_BYTE, img
        )

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    def resizeGL(self, w, h):
        self.update_projection(w, h)

    def update_projection(self, w=None, h=None):
        if w is None or h is None:
            w, h = self.width(), self.height()

        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, w / h if h else 1, 0.1, 1000)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # 1️⃣ Move camera position
        glTranslatef(-self.cam_x, -self.cam_y, -self.cam_z)

        # 2️⃣ Rotate view (TRUE 360 ROTATION)
        glRotatef(self.pitch, 1, 0, 0)
        glRotatef(self.yaw, 0, 1, 0)

        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        quad = gluNewQuadric()
        gluQuadricTexture(quad, GL_TRUE)
        gluQuadricOrientation(quad, GLU_INSIDE)
        gluSphere(quad, 500, 64, 64)


    # ---------------- INPUT ---------------- #

    def mousePressEvent(self, event):
        self.last_x = event.x()
        self.last_y = event.y()

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_x
        dy = event.y() - self.last_y

        self.yaw += dx * 0.2
        self.pitch += dy * 0.2
        self.pitch = max(-89, min(89, self.pitch))

        self.last_x = event.x()
        self.last_y = event.y()
        self.update()

    def keyPressEvent(self, event):
        self.keys.add(event.key())

        if event.key() == Qt.Key_Escape:
            QApplication.quit()

    def keyReleaseEvent(self, event):
        self.keys.discard(event.key())

    # ---------------- MOVEMENT ---------------- #

    def update_movement(self):
        speed = 0.2

        rad = math.radians(self.yaw)
        forward_x = math.sin(rad)
        forward_z = -math.cos(rad)

        right_x = math.cos(rad)
        right_z = math.sin(rad)

        if Qt.Key_W in self.keys:
            self.cam_x += forward_x * speed
            self.cam_z += forward_z * speed

        if Qt.Key_S in self.keys:
            self.cam_x -= forward_x * speed
            self.cam_z -= forward_z * speed

        if Qt.Key_A in self.keys:
            self.cam_x -= right_x * speed
            self.cam_z -= right_z * speed

        if Qt.Key_D in self.keys:
            self.cam_x += right_x * speed
            self.cam_z += right_z * speed

        if Qt.Key_Q in self.keys:
            self.cam_y -= speed

        if Qt.Key_E in self.keys:
            self.cam_y += speed

        if Qt.Key_Plus in self.keys or Qt.Key_Equal in self.keys:
            self.fov = max(30, self.fov - 1)
            self.update_projection()

        if Qt.Key_Minus in self.keys:
            self.fov = min(120, self.fov + 1)
            self.update_projection()

            # Prevent drifting off center (VR-correct)
            self.cam_x = 0.0
            self.cam_y = 0.0
            self.cam_z = 0.0

        self.update()


class MainWindow(QMainWindow):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("360 VR Image Viewer")
        self.setFixedSize(1280, 720)

        self.viewer = PanoramaViewer(image_path)
        self.setCentralWidget(self.viewer)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    image_path, _ = QFileDialog.getOpenFileName(
        None,
        "Select 360 Image",
        "",
        "360 Images (*.jpg *.png *.hdr *jpeg)"
    )

    if not image_path:
        sys.exit(0)

    window = MainWindow(image_path)
    window.show()
    sys.exit(app.exec_())
