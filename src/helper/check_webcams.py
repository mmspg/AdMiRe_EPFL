import sys
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *
  
# Main window class
class MainWindow(QMainWindow):
  
    # constructor
    def __init__(self):
        super().__init__()
  
        # setting geometry
        self.setGeometry(100, 100,
                         800, 600)
  
        # setting style sheet
        self.setStyleSheet("background : lightgrey;")
  
        # getting available cameras
        self.available_cameras = QCameraInfo.availableCameras()
        print(self.available_cameras)
  
        # if no camera found
        if not self.available_cameras:
            # exit the code
            sys.exit()
  
        # creating a status bar
        self.status = QStatusBar()
  
        # setting style sheet to the status bar
        self.status.setStyleSheet("background : white;")
  
        # adding status bar to the main window
        self.setStatusBar(self.status)
  
        # path to save
        self.save_path = ""
  
        # creating a QCameraViewfinder object
        self.viewfinder = QCameraViewfinder()
  
        # showing this viewfinder
        self.viewfinder.show()
  
        # making it central widget of main window
        self.setCentralWidget(self.viewfinder)
  
        # Set the default camera.
        self.select_camera(0)
  
        # creating a tool bar
        toolbar = QToolBar("Camera Tool Bar")
  
        # adding tool bar to main window
        self.addToolBar(toolbar)
  
  
        # creating a combo box for selecting camera
        camera_selector = QComboBox()
  
        # adding status tip to it
        camera_selector.setStatusTip("Choose camera")
  
        # adding tool tip to it
        camera_selector.setToolTip("Select Camera")
        camera_selector.setToolTipDuration(2500)
  
        # adding items to the combo box
        camera_selector.addItems([camera.description()
                                  for camera in self.available_cameras])
  
        # adding action to the combo box
        # calling the select camera method
        camera_selector.currentIndexChanged.connect(self.select_camera)
  
        # adding this to tool bar
        toolbar.addWidget(camera_selector)
  
        # setting tool bar stylesheet
        toolbar.setStyleSheet("background : white;")
  
        # setting window title
        self.setWindowTitle("Index 0")
  
        # showing the main window
        self.show()
  
    # method to select camera
    def select_camera(self, i):
        # setting window title
        self.setWindowTitle(f"Index {i}")
  
        # getting the selected camera
        self.camera = QCamera(self.available_cameras[i])
  
        # setting view finder to the camera
        self.camera.setViewfinder(self.viewfinder)
  
        # if any error occur show the alert
        self.camera.error.connect(lambda: self.alert(self.camera.errorString()))
  
        # start the camera
        self.camera.start()
  
        # getting current camera name
        self.current_camera_name = self.available_cameras[i].description()
  
        # initial save sequence
        self.save_seq = 0
  
    # method for alerts
    def alert(self, msg):
  
        # error message
        error = QErrorMessage(self)
  
        # setting text to the error message
        error.showMessage(msg)
  
# Driver code
if __name__ == "__main__" :
    
  # create pyqt5 app
  App = QApplication(sys.argv)
  
  # create the instance of our Window
  window = MainWindow()
  
  # start the app
  sys.exit(App.exec())