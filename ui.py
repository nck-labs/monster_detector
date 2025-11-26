"""
Interface gráfica com captura ROI em tempo real
"""

import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QGroupBox, 
    QCheckBox, QSpinBox, QFormLayout
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QFont
from pathlib import Path
from datetime import datetime
import win32api

import config
from detector import MonsterDetector, DetectionResult
from screen_capture import ScreenCapture, ROISelector, ROI


class DetectionThread(QThread):
    """Thread para detecção contínua em tempo real"""
    result_ready = pyqtSignal(object, object)  # (result, vis_image)
    error_occurred = pyqtSignal(str)
    debug_log = pyqtSignal(str)
    
    def __init__(self, detector, screen_capture, roi, use_template, use_orb):
        super().__init__()
        self.detector = detector
        self.screen_capture = screen_capture
        self.roi = roi
        self.use_template = use_template
        self.use_orb = use_orb
        self.running = False
        self.frame_count = 0
    
    def run(self):
        """Loop de detecção"""
        self.running = True
        self.frame_count = 0
        
        if config.DEBUG_CAPTURE_LOGS:
            self.debug_log.emit(
                f"🔧 Thread iniciada com ROI {self.roi} | Template={self.use_template} | ORB={self.use_orb}"
            )
        
        while self.running:
            try:
                # Captura ROI da tela
                frame = self.screen_capture.capture_roi(self.roi)
                
                if frame is None:
                    self.error_occurred.emit(
                        f"Erro na captura de tela (ROI {self.roi})"
                    )
                    self.msleep(100)
                    continue
                
                self.frame_count += 1
                if (
                    config.DEBUG_CAPTURE_LOGS
                    and (
                        self.frame_count == 1
                        or self.frame_count % config.DEBUG_DETECTION_LOG_INTERVAL == 0
                    )
                ):
                    h, w = frame.shape[:2]
                    self.debug_log.emit(
                        f"📸 Frame #{self.frame_count} capturado ({w}x{h}) dentro de {self.roi}"
                    )
                
                # Executa detecção
                result = self.detector.detect(
                    frame,
                    self.use_template,
                    self.use_orb
                )
                
                # Visualiza resultado
                vis_frame = self.detector.visualize_detection(frame, result)
                
                # Emite resultado
                self.result_ready.emit(result, vis_frame)
                
                # Aguarda próximo frame (controle de FPS)
                self.msleep(config.DETECTION_INTERVAL_MS)
                
            except Exception as e:
                self.error_occurred.emit(f"Erro na detecção: {e}")
                self.msleep(100)
    
    def stop(self):
        """Para thread"""
        self.running = False


class MonsterDetectorUI(QMainWindow):
    """Interface principal com captura ROI em tempo real"""
    
    def __init__(self):
        super().__init__()
        self.detector = None
        self.screen_capture = ScreenCapture()
        self.roi = None
        self.detection_thread = None
        self.is_detecting = False
        
        # Estatísticas
        self.total_detections = 0
        self.successful_detections = 0
        
        # Última posição detectada (coordenadas absolutas da tela)
        self.last_monster_position = None  # (x, y) absoluto
        
        self.init_ui()
        
        # Inicializa captura (desktop por padrão)
        if not self.screen_capture.initialize():
            self.log("✗ Erro ao inicializar captura de tela", error=True)
    
    def init_ui(self):
        """Inicializa interface"""
        self.setWindowTitle(config.WINDOW_TITLE)
        self.setGeometry(100, 100, 700, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Painel esquerdo - Controles
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Painel direito - Visualização
        right_panel = self.create_visualization_panel()
        main_layout.addWidget(right_panel, 2)
    
    def create_control_panel(self) -> QWidget:
        """Cria painel de controles"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Título
        title = QLabel("🎮 Monster Detector")
        title_font = QFont("Arial", 16, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Real-Time ROI Detection")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(subtitle)
        
        # Grupo: Template
        template_group = QGroupBox("1. Template do Monstro")
        template_layout = QVBoxLayout()
        
        self.btn_load_template = QPushButton("📁 Carregar Template")
        self.btn_load_template.clicked.connect(self.load_template)
        template_layout.addWidget(self.btn_load_template)
        
        self.lbl_template_status = QLabel("Nenhum template carregado")
        self.lbl_template_status.setStyleSheet("color: #999; font-size: 10px;")
        template_layout.addWidget(self.lbl_template_status)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Grupo: ROI
        roi_group = QGroupBox("2. Região de Captura (Battle List)")
        roi_layout = QVBoxLayout()
        
        self.btn_select_roi = QPushButton("🎯 Selecionar ROI")
        self.btn_select_roi.clicked.connect(self.select_roi)
        roi_layout.addWidget(self.btn_select_roi)
        
        self.lbl_roi_status = QLabel("Nenhuma região selecionada")
        self.lbl_roi_status.setStyleSheet("color: #999; font-size: 10px;")
        roi_layout.addWidget(self.lbl_roi_status)
        
        roi_group.setLayout(roi_layout)
        layout.addWidget(roi_group)
        
        # Grupo: Opções de detecção
        options_group = QGroupBox("3. Métodos de Detecção")
        options_layout = QVBoxLayout()
        
        self.chk_template = QCheckBox("Template Matching")
        self.chk_template.setChecked(True)
        options_layout.addWidget(self.chk_template)
        
        self.chk_orb = QCheckBox("ORB Feature Matching")
        self.chk_orb.setChecked(True)
        options_layout.addWidget(self.chk_orb)
        
        # Pré-processamento
        self.chk_preprocessing = QCheckBox("Pré-processamento Avançado")
        self.chk_preprocessing.setChecked(getattr(config, 'USE_PREPROCESSING_ENHANCEMENT', True))
        self.chk_preprocessing.stateChanged.connect(self.on_preprocessing_changed)
        options_layout.addWidget(self.chk_preprocessing)
        
        # FPS Control
        fps_layout = QFormLayout()
        self.spin_fps = QSpinBox()
        self.spin_fps.setRange(1, 60)
        self.spin_fps.setValue(config.DETECTION_FPS)
        self.spin_fps.setSuffix(" FPS")
        self.spin_fps.valueChanged.connect(self.on_fps_changed)
        fps_layout.addRow("Taxa de Detecção:", self.spin_fps)
        
        # Threshold Control
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(50, 100)
        self.spin_threshold.setValue(int(config.TEMPLATE_THRESHOLD * 100))
        self.spin_threshold.setSuffix("%")
        self.spin_threshold.valueChanged.connect(self.on_threshold_changed)
        fps_layout.addRow("Threshold:", self.spin_threshold)
        
        options_layout.addLayout(fps_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Botões de controle
        control_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("▶ Iniciar")
        self.btn_start.clicked.connect(self.start_detection)
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        control_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("⏸ Parar")
        self.btn_stop.clicked.connect(self.stop_detection)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        control_layout.addWidget(self.btn_stop)
        
        layout.addLayout(control_layout)
        
        # Botão de mover mouse para monstro
        mouse_group = QGroupBox("4. Ação do Mouse")
        mouse_layout = QVBoxLayout()
        
        self.btn_move_mouse = QPushButton("🖱️ Mover Mouse para Monstro")
        self.btn_move_mouse.clicked.connect(self.move_mouse_to_monster)
        self.btn_move_mouse.setEnabled(False)
        self.btn_move_mouse.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        mouse_layout.addWidget(self.btn_move_mouse)
        
        self.lbl_monster_position = QLabel("Nenhuma posição detectada")
        self.lbl_monster_position.setStyleSheet("color: #999; font-size: 10px;")
        mouse_layout.addWidget(self.lbl_monster_position)
        
        # Calibração de offset
        calibration_layout = QFormLayout()
        
        self.spin_offset_x = QSpinBox()
        self.spin_offset_x.setRange(-100, 100)
        self.spin_offset_x.setValue(getattr(config, 'POSITION_OFFSET_X', 0))
        self.spin_offset_x.setSuffix(" px")
        self.spin_offset_x.valueChanged.connect(self.on_offset_changed)
        calibration_layout.addRow("Offset X:", self.spin_offset_x)
        
        self.spin_offset_y = QSpinBox()
        self.spin_offset_y.setRange(-100, 100)
        self.spin_offset_y.setValue(getattr(config, 'POSITION_OFFSET_Y', 0))
        self.spin_offset_y.setSuffix(" px")
        self.spin_offset_y.valueChanged.connect(self.on_offset_changed)
        calibration_layout.addRow("Offset Y:", self.spin_offset_y)
        
        mouse_layout.addLayout(calibration_layout)
        
        mouse_group.setLayout(mouse_layout)
        layout.addWidget(mouse_group)
        
        # Estatísticas
        stats_group = QGroupBox("Estatísticas")
        stats_layout = QVBoxLayout()
        
        self.lbl_total = QLabel("Total: 0")
        self.lbl_success = QLabel("Sucesso: 0")
        self.lbl_rate = QLabel("Taxa: 0%")
        
        stats_layout.addWidget(self.lbl_total)
        stats_layout.addWidget(self.lbl_success)
        stats_layout.addWidget(self.lbl_rate)
        
        self.btn_reset_stats = QPushButton("🔄 Resetar")
        self.btn_reset_stats.clicked.connect(self.reset_stats)
        stats_layout.addWidget(self.btn_reset_stats)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Log
        log_group = QGroupBox("Log de Eventos")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(250)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        self.btn_clear_log = QPushButton("🗑 Limpar Log")
        self.btn_clear_log.clicked.connect(self.clear_log)
        log_layout.addWidget(self.btn_clear_log)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        return panel
    
    def create_visualization_panel(self) -> QWidget:
        """Cria painel de visualização"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Título
        viz_title = QLabel("Visualização em Tempo Real")
        viz_title.setAlignment(Qt.AlignCenter)
        viz_title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(viz_title)
        
        # Label para imagem
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px solid #cccccc;
                border-radius: 5px;
                background-color: #f0f0f0;
            }
        """)
        self.image_label.setText("Aguardando captura...\n\nSelecione um template e ROI para começar")
        layout.addWidget(self.image_label)
        
        # Status bar
        self.status_label = QLabel("Status: Aguardando")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                padding: 5px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)
        
        return panel
    
    def load_template(self):
        """Carrega template do monstro"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Template do Monstro",
            "",
            "Imagens (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            try:
                self.detector = MonsterDetector(file_path)
                template_name = Path(file_path).name
                self.lbl_template_status.setText(f"✓ {template_name}")
                self.lbl_template_status.setStyleSheet("color: #4CAF50; font-size: 10px;")
                self.log(f"✓ Template carregado: {template_name}")
                self.update_start_button()
            except Exception as e:
                self.log(f"✗ Erro ao carregar template: {e}", error=True)
    
    def select_roi(self):
        """Seleciona região de interesse"""
        self.log("📍 Iniciando seleção de ROI...")
        
        selector = ROISelector(self.screen_capture)
        self.roi = selector.select_roi()
        
        if self.roi:
            x1, y1, x2, y2 = self.roi.coords
            self.lbl_roi_status.setText(
                f"✓ ({x1}, {y1}) → ({x2}, {y2}) [{self.roi.width}x{self.roi.height}]"
            )
            self.lbl_roi_status.setStyleSheet("color: #4CAF50; font-size: 10px;")
            self.log(
                f"✓ ROI selecionado: {self.roi} | Canto sup. ({x1}, {y1}) / inf. ({x2}, {y2})"
            )
            self.update_start_button()
        else:
            self.log("✗ Seleção de ROI cancelada")
    
    def update_start_button(self):
        """Atualiza estado do botão iniciar"""
        can_start = (
            self.detector is not None and 
            self.roi is not None and 
            not self.is_detecting
        )
        self.btn_start.setEnabled(can_start)
    
    def start_detection(self):
        """Inicia detecção em tempo real"""
        if self.is_detecting:
            return
        
        self.is_detecting = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("Status: 🔴 Detectando...")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #4CAF50;
                color: white;
                padding: 5px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        
        self.log("🔍 Detecção em tempo real iniciada")
        if self.roi:
            x1, y1, x2, y2 = self.roi.coords
            self.log(
                f"📐 ROI ativo: ({x1}, {y1}) → ({x2}, {y2}) [{self.roi.width}x{self.roi.height}]"
            )
        
        # Inicia thread de detecção
        self.detection_thread = DetectionThread(
            self.detector,
            self.screen_capture,
            self.roi,
            self.chk_template.isChecked(),
            self.chk_orb.isChecked()
        )
        self.detection_thread.result_ready.connect(self.on_detection_result)
        self.detection_thread.error_occurred.connect(self.on_detection_error)
        self.detection_thread.debug_log.connect(self.on_debug_log)
        self.detection_thread.start()
    
    def stop_detection(self):
        """Para detecção"""
        if not self.is_detecting:
            return
        
        self.is_detecting = False
        
        if self.detection_thread:
            self.detection_thread.stop()
            self.detection_thread.wait(2000)  # Aguarda até 2s
            if self.detection_thread.isRunning():
                self.detection_thread.terminate()
            self.detection_thread = None
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Status: ⏸ Pausado")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #ff9800;
                color: white;
                padding: 5px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        
        self.log("⏸ Detecção pausada")
    
    def on_detection_result(self, result: DetectionResult, vis_image: np.ndarray):
        """Callback para resultado de detecção"""
        # Atualiza visualização
        self.display_image(vis_image)
        
        # Atualiza estatísticas
        self.total_detections += 1
        if result.found:
            self.successful_detections += 1
            
            # Converte posição relativa do ROI para coordenadas absolutas da tela
            if self.roi:
                rel_x, rel_y = result.position
                
                # Aplica offset configurável (calibração)
                offset_x = getattr(config, 'POSITION_OFFSET_X', 0)
                offset_y = getattr(config, 'POSITION_OFFSET_Y', 0)
                
                abs_x = self.roi.x + rel_x + offset_x
                abs_y = self.roi.y + rel_y + offset_y
                self.last_monster_position = (abs_x, abs_y)
                
                # Atualiza label e habilita botão
                offset_info = f" (offset: {offset_x}, {offset_y})" if (offset_x != 0 or offset_y != 0) else ""
                self.lbl_monster_position.setText(
                    f"Última posição: ({abs_x}, {abs_y}){offset_info}"
                )
                self.lbl_monster_position.setStyleSheet("color: #4CAF50; font-size: 10px;")
                self.btn_move_mouse.setEnabled(True)
        
        self.update_stats()
        
        # Log apenas detecções bem-sucedidas (evita spam)
        if result.found:
            self.log(str(result))

    def on_detection_error(self, error_msg: str):
        """Callback para erro de detecção"""
        self.log(error_msg, error=True)
    
    def on_debug_log(self, message: str):
        """Recebe logs detalhados da thread"""
        self.log(message)

    def on_fps_changed(self, value):
        """Atualiza FPS de detecção"""
        config.DETECTION_FPS = value
        config.DETECTION_INTERVAL_MS = int(1000 / value)
        self.log(f"⚙ FPS atualizado para: {value}")
    
    def on_threshold_changed(self, value):
        """Atualiza threshold de detecção"""
        config.TEMPLATE_THRESHOLD = value / 100.0
        self.log(f"⚙ Threshold atualizado para: {value}%")
    
    def on_offset_changed(self):
        """Atualiza offset de calibração"""
        offset_x = self.spin_offset_x.value()
        offset_y = self.spin_offset_y.value()
        config.POSITION_OFFSET_X = offset_x
        config.POSITION_OFFSET_Y = offset_y
        
        # Recalcula posição se houver última detecção
        if self.last_monster_position and self.roi:
            # Remove offset anterior e aplica novo
            old_x, old_y = self.last_monster_position
            # Não podemos recalcular sem a detecção original, então apenas logamos
            self.log(f"⚙ Offset atualizado: X={offset_x}, Y={offset_y}")
    
    def on_preprocessing_changed(self, state):
        """Atualiza configuração de pré-processamento"""
        enabled = state == Qt.Checked
        config.USE_PREPROCESSING_ENHANCEMENT = enabled
        
        # Se o detector existe, precisa recarregar o template com novo processamento
        if self.detector is not None:
            self.log(f"⚙ Pré-processamento {'ativado' if enabled else 'desativado'}. Recarregue o template para aplicar.")
        else:
            self.log(f"⚙ Pré-processamento {'ativado' if enabled else 'desativado'}")

    def update_stats(self):
        """Atualiza estatísticas"""
        self.lbl_total.setText(f"Total: {self.total_detections}")
        self.lbl_success.setText(f"Sucesso: {self.successful_detections}")
        
        if self.total_detections > 0:
            rate = (self.successful_detections / self.total_detections) * 100
            self.lbl_rate.setText(f"Taxa: {rate:.1f}%")
        else:
            self.lbl_rate.setText("Taxa: 0%")

    def reset_stats(self):
        """Reseta estatísticas"""
        self.total_detections = 0
        self.successful_detections = 0
        self.update_stats()
        self.log("🔄 Estatísticas resetadas")

    def display_image(self, image: np.ndarray):
        """Exibe imagem no label"""
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        qt_image = QImage(
            rgb_image.data,
            w,
            h,
            bytes_per_line,
            QImage.Format_RGB888
        )
        
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)

    def log(self, message: str, error: bool = False):
        """Adiciona mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = "red" if error else "black"
        formatted_msg = f'<span style="color: {color};">[{timestamp}] {message}</span>'
        self.log_text.append(formatted_msg)
        
        # Limita linhas do log
        if self.log_text.document().lineCount() > config.LOG_MAX_LINES:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def clear_log(self):
        """Limpa log"""
        self.log_text.clear()
    
    def move_mouse_to_monster(self):
        """Move o mouse para a última posição detectada do monstro"""
        if self.last_monster_position is None:
            self.log("✗ Nenhuma posição de monstro disponível", error=True)
            return
        
        try:
            x, y = self.last_monster_position
            win32api.SetCursorPos((x, y))
            self.log(f"🖱️ Mouse movido para ({x}, {y})")
        except Exception as e:
            self.log(f"✗ Erro ao mover mouse: {e}", error=True)

    def closeEvent(self, event):
        """Cleanup ao fechar"""
        if self.is_detecting:
            self.stop_detection()
        
        self.screen_capture.cleanup()
        event.accept()


def main():
    """Ponto de entrada para iniciar a interface PyQt."""
    app = QApplication.instance()
    created_app = False
    if app is None:
        app = QApplication(sys.argv)
        created_app = True

    window = MonsterDetectorUI()
    window.show()

    # Apenas inicia o loop de eventos se formos responsáveis pelo QApplication
    if created_app:
        return app.exec_()
    return app