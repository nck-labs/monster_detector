"""
Sistema de captura de tela usando BitBlt para performance máxima
"""

import numpy as np
import win32gui
import win32ui
import win32con
import win32api
from typing import Tuple, Optional
from dataclasses import dataclass
from PIL import ImageGrab
import cv2
import config

# Imports para overlay PyQt5
try:
    from PyQt5.QtWidgets import QWidget, QApplication
    from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal
    from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QCursor
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False


@dataclass
class ROI:
    """Região de Interesse"""
    x: int
    y: int
    width: int
    height: int
    
    def __str__(self):
        return f"ROI(x={self.x}, y={self.y}, w={self.width}, h={self.height})"
    
    @property
    def coords(self) -> Tuple[int, int, int, int]:
        """Retorna coordenadas (x1, y1, x2, y2)"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def is_valid(self) -> bool:
        """Verifica se ROI é válido"""
        return self.width > 0 and self.height > 0


class ScreenCapture:
    """
    Captura de tela otimizada usando BitBlt do Windows
    Performance superior ao PIL/mss para captura contínua
    """
    
    def __init__(self):
        """Inicializa contextos de captura"""
        self.hwnd = None
        self.hwndDC = None
        self.mfcDC = None
        self.saveDC = None
        self.saveBitMap = None
        self._initialized = False
        self._name = "Desktop"
    
    def initialize(self, window_title: Optional[str] = None):
        """
        Inicializa contextos de captura
        
        Args:
            window_title: Título da janela (None para desktop inteiro)
        """
        try:
            # Obtém handle da janela
            if window_title:
                self.hwnd = win32gui.FindWindow(None, window_title)
                if not self.hwnd:
                    raise ValueError(f"Janela '{window_title}' não encontrada")
                self._name = window_title
            else:
                self.hwnd = win32gui.GetDesktopWindow()
                self._name = "Desktop"
            
            # Contextos de dispositivo
            self.hwndDC = win32gui.GetWindowDC(self.hwnd)
            self.mfcDC = win32ui.CreateDCFromHandle(self.hwndDC)
            self.saveDC = self.mfcDC.CreateCompatibleDC()
            
            self._initialized = True
            if config.DEBUG_CAPTURE_LOGS:
                print(f"[ScreenCapture] Contexto inicializado ({self._name})")
            return True
            
        except Exception as e:
            print(f"Erro ao inicializar captura: {e}")
            return False
    
    def capture_roi(self, roi: ROI) -> Optional[np.ndarray]:
        """
        Captura região específica da tela usando BitBlt
        
        Args:
            roi: Região de interesse a capturar
            
        Returns:
            Imagem em formato numpy array (BGR) ou None se erro
        """
        if not self._initialized:
            if config.DEBUG_CAPTURE_LOGS:
                print("[ScreenCapture] Contexto não inicializado antes da captura")
            print("ScreenCapture não inicializado. Chame initialize() primeiro.")
            return None
        
        if not roi.is_valid():
            if config.DEBUG_CAPTURE_LOGS:
                print(f"[ScreenCapture] ROI inválido recebido: {roi}")
            print("ROI inválido")
            return None
        
        try:
            if config.DEBUG_CAPTURE_LOGS:
                x1, y1, x2, y2 = roi.coords
                print(
                    f"[ScreenCapture] BitBlt capturando ROI "
                    f"({x1}, {y1}) → ({x2}, {y2}) [{roi.width}x{roi.height}]"
                )

            # Cria bitmap compatível
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(self.mfcDC, roi.width, roi.height)
            self.saveDC.SelectObject(saveBitMap)
            
            # BitBlt - copia pixels da tela para bitmap
            result = self.saveDC.BitBlt(
                (0, 0),  # Destino
                (roi.width, roi.height),  # Tamanho
                self.mfcDC,  # Origem
                (roi.x, roi.y),  # Posição origem
                win32con.SRCCOPY  # Operação de cópia
            )
            
            if not result:
                raise RuntimeError("BitBlt retornou código 0")
            
            # Converte bitmap para numpy array
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            img = np.frombuffer(bmpstr, dtype=np.uint8)
            img.shape = (roi.height, roi.width, 4)  # BGRA
            
            # Remove canal alpha e converte para BGR
            img = img[:, :, :3]
            img = np.ascontiguousarray(img)  # Garante array contíguo
            
            # Cleanup
            win32gui.DeleteObject(saveBitMap.GetHandle())
            
            return img
            
        except Exception as e:
            if config.DEBUG_CAPTURE_LOGS:
                print(f"[ScreenCapture] BitBlt falhou: {e}")
            if getattr(config, "ENABLE_IMAGEGRAB_FALLBACK", False):
                try:
                    if config.DEBUG_CAPTURE_LOGS:
                        print("[ScreenCapture] Tentando fallback com ImageGrab")
                    grab = ImageGrab.grab(bbox=roi.coords)
                    return cv2.cvtColor(np.array(grab), cv2.COLOR_RGB2BGR)
                except Exception as fallback_error:
                    if config.DEBUG_CAPTURE_LOGS:
                        print(f"[ScreenCapture] Fallback ImageGrab falhou: {fallback_error}")
            print(f"Erro na captura: {e}")
            return None
    
    def get_screen_size(self) -> Tuple[int, int]:
        """
        Obtém dimensões da tela/janela
        
        Returns:
            (largura, altura)
        """
        if not self._initialized:
            # Retorna tamanho do desktop como fallback
            return (
                win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
                win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            )
        
        try:
            if self.hwnd == win32gui.GetDesktopWindow():
                return (
                    win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
                    win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                )
            else:
                rect = win32gui.GetWindowRect(self.hwnd)
                return (rect[2] - rect[0], rect[3] - rect[1])
        except:
            return (1920, 1080)  # Fallback
    
    def cleanup(self):
        """Libera recursos"""
        try:
            if self.saveDC:
                self.saveDC.DeleteDC()
            if self.mfcDC:
                self.mfcDC.DeleteDC()
            if self.hwndDC:
                win32gui.ReleaseDC(self.hwnd, self.hwndDC)
            self._initialized = False
        except:
            pass
    
    def __del__(self):
        """Destrutor - garante limpeza"""
        self.cleanup()


class ROIOverlayWidget(QWidget):
    """
    Widget transparente que cobre toda a tela para seleção de ROI
    """
    roi_selected = pyqtSignal(object)  # Emite ROI quando selecionado
    selection_cancelled = pyqtSignal()  # Emite quando cancelado
    
    def __init__(self):
        super().__init__()
        self.start_point = None
        self.end_point = None
        self.selecting = False
        
        # Configura janela transparente e sem bordas
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        
        # Obtém tamanho da tela
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        # Cursor de cruz
        self.setCursor(Qt.CrossCursor)
        
        # Mostra janela
        self.show()
        QApplication.processEvents()
        
    def paintEvent(self, event):
        """Desenha overlay com seleção"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fundo semi-transparente escuro
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # Se há seleção, desenha retângulo
        if self.start_point and self.end_point:
            x1, y1 = self.start_point.x(), self.start_point.y()
            x2, y2 = self.end_point.x(), self.end_point.y()
            
            # Garante ordem correta
            left = min(x1, x2)
            right = max(x1, x2)
            top = min(y1, y2)
            bottom = max(y1, y2)
            
            rect = QRect(left, top, right - left, bottom - top)
            
            # Área selecionada - transparente
            painter.fillRect(rect, QColor(255, 255, 255, 0))
            
            # Borda verde
            pen = QPen(QColor(0, 255, 0), 3)
            painter.setPen(pen)
            painter.drawRect(rect)
            
            # Texto com dimensões
            width = right - left
            height = bottom - top
            text = f"{width} x {height}"
            
            painter.setPen(QPen(QColor(0, 255, 0), 2))
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            
            # Fundo semi-transparente para texto
            text_rect = QRect(left, top - 25, 100, 20)
            painter.fillRect(text_rect, QColor(0, 0, 0, 150))
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
            
            # Coordenadas
            coords_text = f"({left}, {top}) → ({right}, {bottom})"
            coords_rect = QRect(left, bottom + 5, 200, 20)
            painter.fillRect(coords_rect, QColor(0, 0, 0, 150))
            painter.drawText(coords_rect, Qt.AlignLeft | Qt.AlignVCenter, coords_text)
    
    def mousePressEvent(self, event):
        """Primeiro clique - inicia seleção"""
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.selecting = True
            self.update()
    
    def mouseMoveEvent(self, event):
        """Movimento do mouse durante seleção"""
        if self.selecting:
            self.end_point = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Segundo clique - finaliza seleção"""
        if event.button() == Qt.LeftButton and self.selecting:
            self.end_point = event.pos()
            self.selecting = False
            
            if self.start_point and self.end_point:
                x1, y1 = self.start_point.x(), self.start_point.y()
                x2, y2 = self.end_point.x(), self.end_point.y()
                
                # Garante que x1,y1 é canto superior esquerdo
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                
                # Cria ROI
                roi = ROI(
                    x=x1,
                    y=y1,
                    width=x2 - x1,
                    height=y2 - y1
                )
                
                if roi.is_valid():
                    self.roi_selected.emit(roi)
                    self.close()
    
    def keyPressEvent(self, event):
        """ESC cancela seleção"""
        if event.key() == Qt.Key_Escape:
            self.selection_cancelled.emit()
            self.close()


class ROISelector:
    """
    Seletor interativo de ROI com overlay transparente sobre a tela
    """
    
    def __init__(self, screen_capture: ScreenCapture):
        """
        Args:
            screen_capture: Instância de ScreenCapture configurada
        """
        self.screen_capture = screen_capture
        self.selected_roi = None
    
    def select_roi(self, window_name: str = "Selecione a Região (Battle List)") -> Optional[ROI]:
        """
        Inicia seleção interativa de ROI usando overlay transparente sobre a tela
        
        Args:
            window_name: Nome da janela de seleção (ignorado se usar PyQt5)
            
        Returns:
            ROI selecionado ou None se cancelado
        """
        # Tenta usar overlay PyQt5 se disponível
        if PYQT5_AVAILABLE:
            return self._select_roi_overlay()
        else:
            # Fallback para método OpenCV antigo
            return self._select_roi_opencv(window_name)
    
    def _select_roi_overlay(self) -> Optional[ROI]:
        """Seleção usando overlay PyQt5 transparente"""
        from PyQt5.QtCore import QEventLoop
        
        app = QApplication.instance()
        if app is None:
            return None
        
        self.selected_roi = None
        selection_done = False
        
        def on_roi_selected(roi):
            nonlocal self, selection_done
            self.selected_roi = roi
            selection_done = True
            loop.quit()
        
        def on_cancelled():
            nonlocal selection_done
            selection_done = True
            loop.quit()
        
        # Cria overlay
        overlay = ROIOverlayWidget()
        overlay.roi_selected.connect(on_roi_selected)
        overlay.selection_cancelled.connect(on_cancelled)
        
        print("\n" + "="*60)
        print("📍 SELEÇÃO DE ROI - OVERLAY TRANSPARENTE")
        print("="*60)
        print("1. Clique e arraste para selecionar a região")
        print("2. Solte o mouse para confirmar")
        print("3. Pressione ESC para cancelar")
        print("="*60 + "\n")
        
        # Event loop para aguardar seleção
        loop = QEventLoop()
        overlay.roi_selected.connect(loop.quit)
        overlay.selection_cancelled.connect(loop.quit)
        loop.exec_()
        
        overlay.close()
        
        if self.selected_roi:
            x1, y1, x2, y2 = self.selected_roi.coords
            print(f"✓ ROI selecionado: ({x1}, {y1}) até ({x2}, {y2}) -> {self.selected_roi}")
            return self.selected_roi
        else:
            print("✗ Seleção cancelada")
            return None
    
    def _select_roi_opencv(self, window_name: str) -> Optional[ROI]:
        """Método antigo usando OpenCV (fallback)"""
        # Captura tela inteira para seleção
        screen_width, screen_height = self.screen_capture.get_screen_size()
        full_screen_roi = ROI(0, 0, screen_width, screen_height)
        
        screenshot = self.screen_capture.capture_roi(full_screen_roi)
        if screenshot is None:
            # Fallback usando ImageGrab para garantir seleção
            try:
                grab = ImageGrab.grab()
                screenshot = cv2.cvtColor(np.array(grab), cv2.COLOR_RGB2BGR)
                print("⚠ BitBlt indisponível. Usando fallback do ImageGrab.")
            except Exception as e:
                print(f"Erro ao capturar tela para seleção: {e}")
                return None
        
        # Estado para callback
        start_point = [None]
        end_point = [None]
        selecting = [False]
        selected_roi = [None]
        selection_complete = [False]
        
        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                start_point[0] = (x, y)
                selecting[0] = True
                end_point[0] = None
                selection_complete[0] = False
            elif event == cv2.EVENT_MOUSEMOVE and selecting[0]:
                end_point[0] = (x, y)
            elif event == cv2.EVENT_LBUTTONUP:
                end_point[0] = (x, y)
                selecting[0] = False
                if start_point[0] and end_point[0]:
                    x1, y1 = start_point[0]
                    x2, y2 = end_point[0]
                    x1, x2 = min(x1, x2), max(x1, x2)
                    y1, y2 = min(y1, y2), max(y1, y2)
                    selected_roi[0] = ROI(x=x1, y=y1, width=x2-x1, height=y2-y1)
                    selection_complete[0] = selected_roi[0].is_valid()
        
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window_name, mouse_callback)
        
        print("\n" + "="*60)
        print("📍 SELEÇÃO DE ROI (OpenCV)")
        print("="*60)
        print("1. Clique no canto superior esquerdo da região")
        print("2. Clique no canto inferior direito da região")
        print("3. A seleção é confirmada automaticamente no segundo clique")
        print("4. Pressione ESC para cancelar")
        print("="*60 + "\n")
        
        while True:
            display = screenshot.copy()
            if start_point[0] and end_point[0]:
                x1, y1 = start_point[0]
                x2, y2 = end_point[0]
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                overlay = display.copy()
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)
                cv2.addWeighted(overlay, 0.2, display, 0.8, 0, display)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                cv2.putText(display, f"{width}x{height}", (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            cv2.imshow(window_name, display)
            key = cv2.waitKey(1) & 0xFF
            
            if selection_complete[0] and selected_roi[0]:
                cv2.destroyWindow(window_name)
                return selected_roi[0]
            elif key == 27:
                cv2.destroyWindow(window_name)
                return None