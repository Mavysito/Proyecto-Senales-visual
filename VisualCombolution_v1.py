import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg
from scipy import signal
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

class ConvolutionVisualizer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Convolución Dinámica - PyQt6 uwu")
        self.resize(1100, 700)

        # Datos base ampliados para permitir el "deslizamiento"
        self.fs = 500  
        self.t = np.linspace(-2, 2, self.fs * 4, endpoint=False) # Eje de tiempo más amplio
        self.dt = self.t[1] - self.t[0]
        self.signals = [] 

        # Estado de la animación
        self.shift_index = 0
        self.conv_result = np.zeros_like(self.t)
        
        # Timer para la animación
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.animate_step)

        self.setup_ui()
        
        # Forzar exactamente 2 señales para la convolución
        self.add_signal()
        self.add_signal()

    def setup_ui(self):
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        layout = QtWidgets.QHBoxLayout(main_widget)

        # Sidebar
        sidebar = QtWidgets.QWidget()
        sidebar.setFixedWidth(250)
        self.side_layout = QtWidgets.QVBoxLayout(sidebar)
        
        # Controles de animación
        self.btn_play = QtWidgets.QPushButton("▶ Reproducir / Pausa")
        self.btn_play.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        self.btn_play.clicked.connect(self.toggle_animation)
        self.side_layout.addWidget(self.btn_play)
        
        self.btn_reset = QtWidgets.QPushButton("⏹ Reiniciar")
        self.btn_reset.clicked.connect(self.reset_animation)
        self.side_layout.addWidget(self.btn_reset)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)
        self.side_layout.addWidget(self.scroll)

        # Gráficos
        self.win = pg.GraphicsLayoutWidget()
        
        # Plot 1: El proceso (Multiplicación y Deslizamiento)
        self.p1 = self.win.addPlot(title="Proceso: f(τ) [Fija] y g(t-τ) [Móvil]")
        self.p1.showGrid(x=True, y=True)
        self.p1.setYRange(-2, 2)
        
        # Curvas del Plot 1
        self.curve_f = self.p1.plot(pen=pg.mkPen('b', width=2), name="f(t)")
        self.curve_g = self.p1.plot(pen=pg.mkPen('r', width=2), name="g(t-tau)")
        self.curve_prod = self.p1.plot(pen=pg.mkPen('g', width=1, style=QtCore.Qt.PenStyle.DashLine))
        
        # Relleno del área (Integral)
        self.curve_zero = self.p1.plot(self.t, np.zeros_like(self.t), pen=None)
        self.fill = pg.FillBetweenItem(self.curve_zero, self.curve_prod, brush=(0, 255, 0, 80))
        self.p1.addItem(self.fill)

        self.win.nextRow()
        
        # Plot 2: Resultado de la convolución
        self.p2 = self.win.addPlot(title="Resultado de la Convolución (f * g)(t)")
        self.p2.showGrid(x=True, y=True)
        self.curve_conv = self.p2.plot(pen=pg.mkPen('y', width=3))

        layout.addWidget(sidebar)
        layout.addWidget(self.win)

    def add_signal(self):
        if len(self.signals) >= 2:
            return # Solo permitimos 2 señales para la convolución

        new_sig = SignalObject()
        self.signals.append(new_sig)
        
        control = SignalControlWidget(new_sig)
        control.changed.connect(self.reset_animation)
        # Desactivamos el botón de eliminar para forzar siempre 2 señales
        control.findChild(QtWidgets.QPushButton).setEnabled(False) 
        
        self.scroll_layout.addWidget(control)

    def toggle_animation(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(20) # 20 ms por frame (50 fps)

    def reset_animation(self):
        self.timer.stop()
        self.shift_index = 0
        self.conv_result = np.zeros_like(self.t)
        self.curve_conv.setData(self.t, self.conv_result)
        self.update_plots_static() # Dibuja la posición inicial

    def update_plots_static(self):
        if len(self.signals) < 2: return
        
        # Obtenemos las señales completas
        f_data = self.signals[0].get_data(self.t)
        
        # Invertimos la segunda señal para la convolución: g(-tau)
        g_data_raw = self.signals[1].get_data(self.t)
        g_data_inv = np.flip(g_data_raw) 
        
        # Dibujamos f estática
        self.curve_f.setData(self.t, f_data)
        
        # En el frame 0, la señal está al inicio
        return f_data, g_data_inv

    def animate_step(self):
        if len(self.signals) < 2: return
        
        f_data, g_data_inv = self.update_plots_static()

        # Desplazamiento circular (np.roll) simula g(t - tau) moviéndose en el tiempo
        # Comenzamos desde el extremo izquierdo (-len(t)) hacia la derecha
        shift = self.shift_index - len(self.t)
        g_shifted = np.roll(g_data_inv, shift)
        
        # Anulamos los valores que dan la vuelta por el roll (queremos que entre de cero)
        if shift < 0:
            g_shifted[shift:] = 0
        else:
            g_shifted[:shift] = 0

        # Multiplicación punto a punto
        product = f_data * g_shifted
        
        # Actualizar curvas superiores
        self.curve_g.setData(self.t, g_shifted)
        self.curve_prod.setData(self.t, product)
        
        # Calcular el punto actual de la convolución (área)
        area = np.sum(product) * self.dt
        
        # Guardamos el resultado en la posición temporal correspondiente
        current_time_index = self.shift_index
        if current_time_index < len(self.t):
            self.conv_result[current_time_index] = area
            self.curve_conv.setData(self.t[:current_time_index], self.conv_result[:current_time_index])

        # Avanzar frame
        self.shift_index += 10 # Salto de 10 puntos por frame para que la animación sea fluida y rápida
        
        # Detener al final
        if self.shift_index >= len(self.t):
            self.timer.stop()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ConvolutionVisualizer()
    window.show()
    sys.exit(app.exec())