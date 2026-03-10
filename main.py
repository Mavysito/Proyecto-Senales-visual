import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg
from scipy import signal

class SignalObject:
    def __init__(self, type='Seno', freq=5.0, amp=1.0, shift=0.0):
        self.type = type
        self.freq = freq
        self.amp = amp
        self.shift = shift
        self.active = True

    def get_data(self, t):
        if not self.active: return np.zeros_like(t)
        
        # Apply time shift
        t_shifted = t - self.shift
        
        if self.type == 'Seno':
            return self.amp * np.sin(2 * np.pi * self.freq * t_shifted)
        if self.type == 'Cuadrada':
            return self.amp * signal.square(2 * np.pi * self.freq * t_shifted)
        if self.type == 'Diente sierra':
            return self.amp * signal.sawtooth(2 * np.pi * self.freq * t_shifted)
        if self.type == 'Delta':
            data = np.zeros_like(t)
            # Find the index closest to shift
            idx = np.argmin(np.abs(t_shifted))
            data[idx] = self.amp # We scale the single sample by amp
            return data
        if self.type == 'Impulso Cuadrado':
            data = np.zeros_like(t)
            # A pulse of width 1/(2*freq) centered at 'shift'
            width = 1.0 / (2.0 * max(self.freq, 0.001))
            mask = np.abs(t_shifted) < (width / 2.0)
            data[mask] = self.amp
            return data
            
        return np.zeros_like(t)

class SignalControlWidget(QtWidgets.QFrame):
    changed = QtCore.pyqtSignal()
    removed = QtCore.pyqtSignal(object)

    def __init__(self, signal_obj, disable_remove=False):
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.sig = signal_obj
        layout = QtWidgets.QVBoxLayout(self)

        # Tipo
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(["Seno", "Cuadrada", "Diente sierra", "Delta", "Impulso Cuadrado"])
        self.combo.setCurrentText(self.sig.type)
        self.combo.currentTextChanged.connect(self.update_params)
        layout.addWidget(QtWidgets.QLabel("Tipo de Onda:"))
        layout.addWidget(self.combo)

        # Helper to create slider + double spinbox
        def create_slider_spinbox(label_text, min_val, max_val, step, current_val, callback):
            lbl = QtWidgets.QLabel(label_text)
            layout.addWidget(lbl)
            
            row = QtWidgets.QHBoxLayout()
            slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            spin = QtWidgets.QDoubleSpinBox()
            
            # Use a factor to map float to int slider (100 steps per unit)
            factor = 100.0
            slider.setRange(int(min_val * factor), int(max_val * factor))
            slider.setValue(int(current_val * factor))
            
            spin.setRange(min_val, max_val)
            spin.setSingleStep(step)
            spin.setValue(current_val)
            
            # Connect them
            def on_slider(val):
                spin.blockSignals(True)
                spin.setValue(val / factor)
                spin.blockSignals(False)
                callback()
                
            def on_spin(val):
                slider.blockSignals(True)
                slider.setValue(int(val * factor))
                slider.blockSignals(False)
                callback()
                
            slider.valueChanged.connect(on_slider)
            spin.valueChanged.connect(on_spin)
            
            row.addWidget(slider)
            row.addWidget(spin)
            layout.addLayout(row)
            return slider, spin

        self.f_slider, self.f_spin = create_slider_spinbox("Frecuencia (Hz):", 0.1, 100.0, 1.0, self.sig.freq, self.update_params)
        self.a_slider, self.a_spin = create_slider_spinbox("Amplitud:", 0.1, 10.0, 0.1, self.sig.amp, self.update_params)
        self.s_slider, self.s_spin = create_slider_spinbox("Desplazamiento (s):", -2.0, 2.0, 0.1, self.sig.shift, self.update_params)

        if not disable_remove:
            btn_del = QtWidgets.QPushButton("Eliminar")
            btn_del.setStyleSheet("background-color: #ff4444; color: white;")
            btn_del.clicked.connect(lambda: self.removed.emit(self))
            layout.addWidget(btn_del)

    def update_params(self):
        self.sig.type = self.combo.currentText()
        self.sig.freq = self.f_spin.value()
        self.sig.amp = self.a_spin.value()
        self.sig.shift = self.s_spin.value()
        self.changed.emit()

class FFTTabWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.fs = 1000  
        self.t = np.linspace(0, 2, self.fs * 2, endpoint=False) # 2 seconds
        self.signals = [] 

        layout = QtWidgets.QHBoxLayout(self)

        sidebar = QtWidgets.QWidget()
        sidebar.setFixedWidth(300)
        self.side_layout = QtWidgets.QVBoxLayout(sidebar)
        btn_add = QtWidgets.QPushButton("+ Añadir Señal")
        btn_add.clicked.connect(self.add_signal)
        self.side_layout.addWidget(btn_add)
        
        self.scroll = QtWidgets.QScrollArea()
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)
        self.side_layout.addWidget(self.scroll)

        self.win = pg.GraphicsLayoutWidget()
        self.p1 = self.win.addPlot(title="Señal Resultante (Tiempo)")
        self.win.nextRow()
        self.p2 = self.win.addPlot(title="FFT (Frecuencia)")
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
        if widget.sig in self.signals:
            self.signals.remove(widget.sig)
        widget.deleteLater()
        QtCore.QTimer.singleShot(10, self.update_plots)

    def update_plots(self):
        total_y = np.zeros_like(self.t)
        for s in self.signals:
            total_y += s.get_data(self.t)

        n = len(self.t)
        yf = np.fft.rfft(total_y)
        xf = np.fft.rfftfreq(n, 1/self.fs)
        mag = np.abs(yf) * (2.0 / n)

        self.p1.plot(self.t, total_y, clear=True, pen='y')
        self.p2.plot(xf[:200], mag[:200], clear=True, pen='c')


class ConvTabWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.fs = 250  
        self.t = np.linspace(-2, 2, self.fs * 4, endpoint=False)
        self.dt = self.t[1] - self.t[0]
        self.signals = [] 

        self.shift_index = 0
        self.conv_result = np.zeros_like(self.t)
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.animate_step)

        self.setup_ui()
        self.add_signal(tipo='Seno')
        self.add_signal(tipo='Cuadrada')
        self.reset_animation()

    def setup_ui(self):
        layout = QtWidgets.QHBoxLayout(self)

        sidebar = QtWidgets.QWidget()
        sidebar.setFixedWidth(300)
        self.side_layout = QtWidgets.QVBoxLayout(sidebar)
        
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

        self.win = pg.GraphicsLayoutWidget()
        
        self.p1 = self.win.addPlot(title="Proceso: f(τ) [Fija] y g(t-τ) [Móvil]")
        self.p1.showGrid(x=True, y=True)
        self.p1.setYRange(-5, 5)
        
        self.curve_f = self.p1.plot(pen=pg.mkPen('b', width=2), name="f(t)")
        self.curve_g = self.p1.plot(pen=pg.mkPen('r', width=2), name="g(t-tau)")
        self.curve_prod = self.p1.plot(pen=pg.mkPen('g', width=1, style=QtCore.Qt.PenStyle.DashLine))
        
        self.curve_zero = self.p1.plot(self.t, np.zeros_like(self.t), pen=None)
        self.fill = pg.FillBetweenItem(self.curve_zero, self.curve_prod, brush=(0, 255, 0, 80))
        self.p1.addItem(self.fill)

        self.win.nextRow()
        
        self.p2 = self.win.addPlot(title="Resultado de la Convolución (f * g)(t)")
        self.p2.showGrid(x=True, y=True)
        self.curve_conv = self.p2.plot(pen=pg.mkPen('y', width=3))

        layout.addWidget(sidebar)
        layout.addWidget(self.win)

    def add_signal(self, tipo='Seno'):
        if len(self.signals) >= 2:
            return 
        new_sig = SignalObject(type=tipo)
        self.signals.append(new_sig)
        
        control = SignalControlWidget(new_sig, disable_remove=True)
        control.changed.connect(self.reset_animation)
        
        self.scroll_layout.addWidget(control)

    def toggle_animation(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(20)

    def reset_animation(self):
        self.timer.stop()
        self.shift_index = 0
        self.conv_result = np.zeros_like(self.t)
        self.curve_conv.setData(self.t, self.conv_result)
        self.update_plots_static()

    def update_plots_static(self):
        if len(self.signals) < 2: return
        
        f_data = self.signals[0].get_data(self.t)
        g_data_raw = self.signals[1].get_data(self.t)
        g_data_inv = np.flip(g_data_raw) 
        
        self.curve_f.setData(self.t, f_data)
        
        # We start animation shift at left-most edge:
        g_shifted = np.roll(g_data_inv, -len(self.t))
        g_shifted[:-len(self.t)] = 0
        self.curve_g.setData(self.t, g_shifted)
        self.curve_prod.setData(self.t, np.zeros_like(self.t))
        
    def animate_step(self):
        if len(self.signals) < 2: return
        
        f_data = self.signals[0].get_data(self.t)
        g_data_raw = self.signals[1].get_data(self.t)
        g_data_inv = np.flip(g_data_raw)

        shift = self.shift_index - len(self.t)
        g_shifted = np.roll(g_data_inv, shift)
        
        if shift < 0:
            g_shifted[shift:] = 0
        else:
            g_shifted[:shift] = 0

        product = f_data * g_shifted
        
        self.curve_g.setData(self.t, g_shifted)
        self.curve_prod.setData(self.t, product)
        
        area = np.sum(product) * self.dt
        
        current_time_index = self.shift_index
        if current_time_index < len(self.t):
            self.conv_result[current_time_index] = area
            self.curve_conv.setData(self.t[:current_time_index], self.conv_result[:current_time_index])

        self.shift_index += max(1, int(len(self.t) / 200)) # Advance
        
        if self.shift_index >= len(self.t):
            self.timer.stop()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visualizador Unificado: FFT y Convolución")
        self.resize(1200, 750)
        
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.fft_tab = FFTTabWidget()
        self.conv_tab = ConvTabWidget()
        
        self.tabs.addTab(self.fft_tab, "Análisis FFT (Múltiples Señales)")
        self.tabs.addTab(self.conv_tab, "Animación de Convolución (2 Señales)")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
