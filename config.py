"""
Configurações do sistema de detecção de monstros
"""

# Escalas para detecção multi-escala (8x8 até 128x128)
SCALES = [
    0.0625,  # 8x8 (se original for 128x128)
    0.125,   # 16x16
    0.25,    # 32x32
    0.5,     # 64x64
    0.75,    # 96x96
    1.0,     # 128x128
    1.25,    # 160x160
    1.5      # 192x192
]

# Limiar de confiança para Template Matching (0-1)
TEMPLATE_THRESHOLD = 0.65

# Limiar de matches para ORB
ORB_MIN_MATCHES = 10

# Número de features ORB a detectar
ORB_FEATURES = 500

# Parâmetros de pré-processamento
BLUR_KERNEL = (3, 3)
BILATERAL_D = 9
BILATERAL_SIGMA_COLOR = 75
BILATERAL_SIGMA_SPACE = 75
USE_PREPROCESSING_ENHANCEMENT = True  # Se False, usa apenas escala de cinza (mais rápido, menos processamento)
CLAHE_CLIP_LIMIT = 1.5  # Limite de contraste para CLAHE (menor = menos agressivo)

# Captura de tela / ROI
ROI_COLOR = (0, 255, 0)  # Verde para seleção
ROI_THICKNESS = 2
ROI_ALPHA = 0.3  # Transparência do overlay

# Detecção em tempo real
DETECTION_FPS = 10  # Frequência de atualização (detecções por segundo)
DETECTION_INTERVAL_MS = int(1000 / DETECTION_FPS)

# UI
WINDOW_TITLE = "Monster Detector System - Real Time"
LOG_MAX_LINES = 100
PREVIEW_UPDATE_FPS = 30  # FPS do preview da captura

# Debug / Logs
DEBUG_CAPTURE_LOGS = True  # Ativa logs detalhados de captura/detecção
DEBUG_DETECTION_LOG_INTERVAL = 30  # Intervalo de frames para logar progresso
ENABLE_IMAGEGRAB_FALLBACK = True  # Usa ImageGrab se BitBlt falhar
SAVE_DEBUG_IMAGES = False  # Se True, salva imagens processadas para debug (pode ser lento)

# Calibração de posição do mouse
USE_CENTER_POSITION = True  # Se True, usa centro do template; se False, usa canto superior esquerdo
POSITION_OFFSET_X = 0  # Offset em pixels no eixo X (pode ser negativo)
POSITION_OFFSET_Y = 0  # Offset em pixels no eixo Y (pode ser negativo)