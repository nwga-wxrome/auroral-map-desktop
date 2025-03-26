import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QToolBar, QPushButton, QLabel
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QSurfaceFormat, QPainter, QPen, QColor
from OpenGL.GL import *
from OpenGL.GLU import *
import requests
from PIL import Image
from io import BytesIO
import os
from aurora_data import AuroraData

class GlobeCamera:
    def __init__(self):
        self.latitude = 0  # 0 = equator, 90 = north pole, -90 = south pole
        self.longitude = 0  # 0 = prime meridian, positive = east, negative = west
        self.distance = 3.0
        self.up_vector = (0, 1, 0)  # Always keep "up" pointing north
        self.vertical_angle = 45  # Add default vertical viewing angle
        
    def get_eye_position(self):
        # Calculate position with both longitude rotation and vertical angle
        lon_rad = np.radians(self.longitude)
        vert_rad = np.radians(self.vertical_angle)
        
        # Calculate position using spherical coordinates
        x = self.distance * np.cos(vert_rad) * np.sin(lon_rad)
        y = self.distance * np.sin(vert_rad)
        z = self.distance * np.cos(vert_rad) * np.cos(lon_rad)
        return (x, y, z)

class CompassWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self.heading = 0

    def setHeading(self, degrees):
        self.heading = degrees % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # White background for better visibility
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        
        # Draw compass circle
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(10, 10, 80, 80)
        
        # Center and rotate
        painter.translate(50, 50)
        painter.rotate(-self.heading)
        
        # Draw north arrow in red
        painter.setPen(QPen(QColor(255, 0, 0), 3))
        painter.drawLine(0, -30, 0, 30)
        # Draw east-west in white
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(-30, 0, 30, 0)
        
        # Reset rotation for text
        painter.rotate(self.heading)
        painter.drawText(-5, -40, "N")
        painter.drawText(-5, 50, "S")
        painter.drawText(40, 5, "E")
        painter.drawText(-45, 5, "W")

class AuroraGlobeWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera = GlobeCamera()
        self.last_pos = None
        self.earth_texture = None
        self.aurora_texture = None
        self.compass = None
        self.quadric = None
        self.initialized = False
        self.aurora = AuroraData()
        self.initializeFormat()
        self.setupTimers()

    def initializeFormat(self):
        format = QSurfaceFormat()
        format.setDepthBufferSize(24)
        format.setSamples(4)
        format.setVersion(2, 1)
        QSurfaceFormat.setDefaultFormat(format)
        self.setFormat(format)

    def setupTimers(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_aurora_data)
        self.timer.start(300000)  # Update every 5 minutes

    def initializeGL(self):
        if self.initialized:
            return
            
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Configure quadric for proper texture mapping
        self.quadric = gluNewQuadric()
        gluQuadricTexture(self.quadric, GL_TRUE)
        gluQuadricNormals(self.quadric, GLU_SMOOTH)
        gluQuadricOrientation(self.quadric, GLU_OUTSIDE)
        gluQuadricDrawStyle(self.quadric, GLU_FILL)
        
        # Load textures
        self.download_earth_texture()
        if os.path.exists("earth_texture.jpg"):
            self.earth_texture = self.load_texture("earth_texture.jpg")
        self.fetch_aurora_data()
        
        self.initialized = True

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, width / height, 0.1, 100.0)

    def paintGL(self):
        try:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            eye = self.camera.get_eye_position()
            gluLookAt(eye[0], -eye[1], eye[2], 
                     0, 0, 0,
                     0, 1, 0)

            glRotatef(-90, 1, 0, 0)

            # Draw Earth first
            if self.earth_texture and self.quadric:
                glEnable(GL_TEXTURE_2D)
                glDisable(GL_BLEND)
                glBindTexture(GL_TEXTURE_2D, self.earth_texture)
                gluSphere(self.quadric, 1.0, 100, 100)
            
            # Draw Aurora overlay
            if self.aurora_texture and self.quadric:
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE)
                glBindTexture(GL_TEXTURE_2D, self.aurora_texture)
                gluSphere(self.quadric, 1.01, 100, 100)
            
            glDisable(GL_BLEND)
            glDisable(GL_TEXTURE_2D)
            
        except Exception as e:
            print(f"Error in paintGL: {e}")

    def draw_textured_sphere(self, texture, radius):
        glBindTexture(GL_TEXTURE_2D, texture)
        quadric = gluNewQuadric()
        gluQuadricTexture(quadric, GL_TRUE)
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluSphere(quadric, radius, 50, 50)
        gluDeleteQuadric(quadric)

    def mousePressEvent(self, event):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_pos is None:
            return

        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()
        
        # Handle both horizontal and vertical movement
        self.camera.longitude += dx * 0.5
        self.camera.vertical_angle = max(-85, min(85, self.camera.vertical_angle - dy * 0.5))
        
        # Keep longitude in range -180 to 180
        self.camera.longitude = ((self.camera.longitude + 180) % 360) - 180
        
        self.last_pos = event.pos()
        self.update_compass()
        self.update()

    def mouseReleaseEvent(self, event):
        self.last_pos = None

    def wheelEvent(self, event):
        self.camera.distance = max(2, min(10, 
            self.camera.distance - event.angleDelta().y() / 120 * 0.1))
        self.update()

    def update_compass(self):
        if self.compass:
            self.compass.setHeading(self.camera.longitude % 360)

    def set_view(self, lat, lon):
        self.camera.latitude = lat
        self.camera.longitude = lon
        self.camera.vertical_angle = 45  # Reset vertical angle when setting view
        self.update_compass()
        self.update()

    def align_north_south(self):
        self.camera.longitude = 0
        self.update_compass()
        self.update()

    def view_north_america(self):
        """Position the globe to view North America"""
        self.set_view(45, -100)  # Keep latitude positive for northern hemisphere

    def download_earth_texture(self):
        if not os.path.exists("earth_texture.jpg"):
            try:
                url = "https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73909/world.topo.bathy.200412.3x5400x2700.jpg"
                response = requests.get(url)
                if response.status_code == 200:
                    with open("earth_texture.jpg", "wb") as f:
                        f.write(response.content)
            except Exception as e:
                print(f"Failed to download Earth texture: {e}")

    def load_texture(self, image_path=None, image_data=None):
        try:
            if image_path:
                image = Image.open(image_path)
            elif image_data:
                image = Image.fromarray(image_data)
            else:
                return None

            image = image.transpose(Image.FLIP_TOP_BOTTOM)
            image = image.convert('RGBA')
            img_data = np.array(image)
            img_data = img_data.tobytes()

            texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture)
            
            # Set better texture parameters
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            
            width, height = image.size
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, 
                        GL_RGBA, GL_UNSIGNED_BYTE, img_data)
            glGenerateMipmap(GL_TEXTURE_2D)
            
            return texture
        except Exception as e:
            print(f"Error loading texture: {e}")
            return None

    def fetch_aurora_data(self):
        try:
            aurora_map = self.aurora.fetch_data()
            if aurora_map is not None:
                self.aurora_texture = self.aurora.create_texture(aurora_map)
                self.update()
        except Exception as e:
            print(f"Error updating aurora: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aurora Forecast Globe")
        
        # Create toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        
        # Add compass widget
        self.compass = CompassWidget()
        self.toolbar.addWidget(self.compass)
        
        # Add orientation button with updated text
        self.orient_button = QPushButton("Align to North")
        self.toolbar.addWidget(self.orient_button)
        
        # Add North America view button
        self.na_button = QPushButton("View North America")
        self.toolbar.addWidget(self.na_button)
        
        # Create and set central widget
        self.globe_widget = AuroraGlobeWidget()
        self.globe_widget.compass = self.compass
        self.setCentralWidget(self.globe_widget)
        
        # Connect buttons
        self.orient_button.clicked.connect(self.globe_widget.align_north_south)
        self.na_button.clicked.connect(self.globe_widget.view_north_america)
        
        self.resize(800, 600)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
