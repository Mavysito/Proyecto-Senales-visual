#matematicas
import numpy as np

#grafica chao mathplot
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg

#fourier y señales importantes uwu
from scipy import signal
from scipy.fft import fft, fftfreq

import sys

#clase de las ondas uwu simplificada
class SignalObject:
    def __init__(self,type='sine',freq=1.0,amp=1.0):
        self.type = type
        self.freq = 5.0
        self.amp = 1.0
        self.active = True

    def get_data(self,t):
        if not self.active: return np.zeros_like(t)
        if self.type == 'Seno':
            return self.amp*np.sin(2*np.pi*self.freq*t)
        if self.type == 'Cuadrada':
            return self.amp*signal.square(2*np.pi*self.freq*t)
        if self.type == 'Diente sierra':
            return self.amp*signal.sawtooth(2*np.pi*self.freq*t)
        return np.zeros_like(t)

# --- INTERFAZ DE CONTROL INDIVIDUAL ---
class SignalControlWidget(QtWidgets.QFrame):
    """Cajita de control para CADA señal de la lista"""
    changed = QtCore.pyqtSignal()
    removed = QtCore.pyqtSignal(object)

    def __init__(self, signal_obj):
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.sig = signal_obj
        layout = QtWidgets.QVBoxLayout(self)

        # Selector de tipo
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(["Seno", "Cuadrada", "Diente sierra"]) 
        self.combo.currentTextChanged.connect(self.update_params) #esta esta curiosa
        
        # Sliders (Freq y Amp)
        self.f_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.f_slider.setRange(1, 100) #rango de valores
        self.f_slider.setValue(int(self.sig.freq)) #setea el valor (ojo int)
        self.f_slider.valueChanged.connect(self.update_params) #linea de funcionamiento

        # Botón borrar
        btn_del = QtWidgets.QPushButton("Eliminar") # lo que tiene escrito
        btn_del.setStyleSheet("background-color: #ff4444; color: white;") #estilo lo de menos
        btn_del.clicked.connect(lambda: self.removed.emit(self)) #define todo el funcionamiento xd

        #layout para mostrar lo demas para hacer su funcionamiento
        layout.addWidget(QtWidgets.QLabel(f"Tipo de Onda:"))
        layout.addWidget(self.combo)
        layout.addWidget(QtWidgets.QLabel("Frecuencia:"))
        layout.addWidget(self.f_slider)
        layout.addWidget(btn_del)

    def update_params(self):
        self.sig.type = self.combo.currentText()
        self.sig.freq = float(self.f_slider.value())
        self.changed.emit()

# --- VENTANA PRINCIPAL ---
class FFTVisualizer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFT Explorer V2 - PyQt6")
        self.resize(1000, 600)

        # Datos base
        self.fs = 1000  # Freq muestreo
        self.t = np.linspace(0, 1, self.fs, endpoint=False) #linea de tiempo 
        self.signals = [] # Lista de objetos SignalObject

        # UI Layout
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        layout = QtWidgets.QHBoxLayout(main_widget)

        # Sidebar #barra con las señales
        sidebar = QtWidgets.QWidget()
        sidebar.setFixedWidth(250)
        self.side_layout = QtWidgets.QVBoxLayout(sidebar)
        btn_add = QtWidgets.QPushButton("+ Añadir Señal")
        btn_add.clicked.connect(self.add_signal)
        self.side_layout.addWidget(btn_add)
        
        # Área de SCROLL para los controles
        self.scroll = QtWidgets.QScrollArea()
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)
        self.side_layout.addWidget(self.scroll)

        # Gráficos
        self.win = pg.GraphicsLayoutWidget()
        self.p1 = self.win.addPlot(title="Señal Resultante (Tiempo)") #señal en el tiempo
        self.win.nextRow()
        self.p2 = self.win.addPlot(title="FFT (Frecuencia)") #señal en frecuencia
        self.p1.showGrid(x=True, y=True)
        self.p2.showGrid(x=True, y=True)
        self.p2.setLabel('bottom', 'Frecuencia', units='Hz')

        layout.addWidget(sidebar)
        layout.addWidget(self.win)

    def add_signal(self):
        new_sig = SignalObject()
        self.signals.append(new_sig)
        
        control = SignalControlWidget(new_sig)
        control.changed.connect(self.update_plots)
        control.removed.connect(self.remove_signal)
        
        self.scroll_layout.addWidget(control)
        self.update_plots()

    def remove_signal(self, widget):
        self.signals.remove(widget.sig)
        widget.deleteLater()
        QtCore.QTimer.singleShot(10, self.update_plots) # Espera un poco a que se destruya

    #logica del programa, lo demas morralla visual
    def update_plots(self):
        # 1. Sumar señales
        total_y = np.zeros_like(self.t)
        for s in self.signals:
            total_y += s.get_data(self.t)

        # 2. FFT
        n = len(self.t)
        yf = np.fft.rfft(total_y)
        xf = np.fft.rfftfreq(n, 1/self.fs)
        mag = np.abs(yf) * (2.0 / n)

        # 3. Dibujar
        self.p1.plot(self.t, total_y, clear=True, pen='y')
        self.p2.plot(xf[:100], mag[:100], clear=True, pen='c') # Limitamos a 100Hz para ver mejor
     

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = FFTVisualizer()
    window.show()
    sys.exit(app.exec())

    






