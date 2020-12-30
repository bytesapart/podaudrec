import sys
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import queue
import numpy as np
import sounddevice as sd
import soundfile as sf
import tempfile

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtMultimedia import QAudioDeviceInfo, QAudio


matplotlib.use('Qt5Agg')
input_audio_deviceInfos = QAudioDeviceInfo.availableDevices(QAudio.AudioInput)


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        fig.tight_layout()


class LivePlotApp(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi('main.ui', self)
        self.resize(888, 600)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("PyShine.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        self.threadpool = QtCore.QThreadPool()
        self.threadpool.setMaxThreadCount(1)
        self.devices_list = []
        for device in input_audio_deviceInfos:
            self.devices_list.append(device.deviceName())

        self.comboBox.addItems(self.devices_list)
        self.comboBox.currentIndexChanged['QString'].connect(self.update_now)
        self.comboBox.setCurrentIndex(0)

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.ui.gridLayout_4.addWidget(self.canvas, 2, 1, 1, 1)
        self.reference_plot = None
        self.q = queue.Queue(maxsize=20)

        self.device = 0
        self.window_length = 1000
        self.downsample = 1
        self.channels = [1]
        self.interval = 30

        device_info = sd.query_devices(self.device, 'input')
        self.samplerate = device_info['default_samplerate']
        length = int(self.window_length * self.samplerate / (1000 * self.downsample))
        sd.default.samplerate = self.samplerate

        self.plotdata = np.zeros((length, len(self.channels)))
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.interval)  # msec
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()
        self.data = [0]
        self.lineEdit.textChanged['QString'].connect(self.update_window_length)
        self.lineEdit_2.textChanged['QString'].connect(self.update_sample_rate)
        self.lineEdit_3.textChanged['QString'].connect(self.update_down_sample)
        self.lineEdit_4.textChanged['QString'].connect(self.update_interval)
        self.pushButton.clicked.connect(self.start_worker)
        self.pushButton_2.clicked.connect(self.stop_worker)
        self.worker = None
        self.go_on = False
        filename = tempfile.mktemp(
            prefix='podaudrec_', suffix='.wav', dir='')
        self.sound_file = sf.SoundFile(filename, mode='x', samplerate=int(self.samplerate),
                                       channels=max(self.channels))

    def getAudio(self):
        try:
            QtWidgets.QApplication.processEvents()

            def audio_callback(indata, frames, time, status):
                self.q.put(indata[::self.downsample, [0]])

            stream = sd.InputStream(blocksize=2048, device=self.device, channels=max(self.channels), samplerate=self.samplerate,
                                    callback=audio_callback)

            with self.sound_file:
                with stream:

                    while True:
                        QtWidgets.QApplication.processEvents()
                        if self.go_on:
                            break

            self.pushButton.setEnabled(True)
            self.lineEdit.setEnabled(True)
            self.lineEdit_2.setEnabled(True)
            self.lineEdit_3.setEnabled(True)
            self.lineEdit_4.setEnabled(True)
            self.comboBox.setEnabled(True)

        except Exception as e:
            print("ERROR: ", e)
            pass

    def start_worker(self):

        self.lineEdit.setEnabled(False)
        self.lineEdit_2.setEnabled(False)
        self.lineEdit_3.setEnabled(False)
        self.lineEdit_4.setEnabled(False)
        self.comboBox.setEnabled(False)
        self.pushButton.setEnabled(False)
        self.canvas.axes.clear()

        self.go_on = False
        self.worker = Worker(self.start_stream, )
        self.threadpool.start(self.worker)
        self.reference_plot = None
        self.timer.setInterval(self.interval)  # msec

    def stop_worker(self):

        self.go_on = True
        with self.q.mutex:
            self.q.queue.clear()

    # self.timer.stop()

    def start_stream(self):

        self.getAudio()

    def update_now(self, value):
        self.device = self.devices_list.index(value)

    def update_window_length(self, value):
        self.window_length = int(value)
        length = int(self.window_length * self.samplerate / (1000 * self.downsample))
        self.plotdata = np.zeros((length, len(self.channels)))

    def update_sample_rate(self, value):
        self.samplerate = int(value)
        sd.default.samplerate = self.samplerate
        length = int(self.window_length * self.samplerate / (1000 * self.downsample))
        self.plotdata = np.zeros((length, len(self.channels)))

    def update_down_sample(self, value):
        self.downsample = int(value)
        length = int(self.window_length * self.samplerate / (1000 * self.downsample))
        self.plotdata = np.zeros((length, len(self.channels)))

    def update_interval(self, value):
        self.interval = int(value)

    def update_plot(self):
        try:

            print('ACTIVE THREADS:', self.threadpool.activeThreadCount(), end=" \r")
            while self.go_on is False:
                QtWidgets.QApplication.processEvents()
                try:
                    self.data = self.q.get_nowait()
                    self.sound_file.write(self.data)

                except queue.Empty:
                    break

                shift = len(self.data)
                self.plotdata = np.roll(self.plotdata, -shift, axis=0)
                self.plotdata[-shift:, :] = self.data
                self.ydata = self.plotdata[:]
                self.canvas.axes.set_facecolor((0, 0, 0))

                if self.reference_plot is None:
                    plot_refs = self.canvas.axes.plot(self.ydata, color=(0, 1, 0.29))
                    self.reference_plot = plot_refs[0]
                else:
                    self.reference_plot.set_ydata(self.ydata)

            self.canvas.axes.yaxis.grid(True, linestyle='--')
            start, end = self.canvas.axes.get_ylim()
            self.canvas.axes.yaxis.set_ticks(np.arange(start, end, 0.1))
            self.canvas.axes.yaxis.set_major_formatter(ticker.FormatStrFormatter('%0.1f'))
            self.canvas.axes.set_ylim(ymin=-0.5, ymax=0.5)

            self.canvas.draw()
        except Exception as e:
            print("Error:", e)
            pass


class Worker(QtCore.QRunnable):

    def __init__(self, function, *args, **kwargs):
        super(Worker, self).__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        self.function(*self.args, **self.kwargs)


app = QtWidgets.QApplication(sys.argv)
mainWindow = LivePlotApp()
mainWindow.show()
sys.exit(app.exec_())
