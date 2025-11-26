# 🎮 Monster Detector - Tibia Bot

Sistema de detecção de monstros em tempo real para Tibia usando visão computacional.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.x-orange.svg)
![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

## 📋 Descrição

O **Monster Detector** é uma ferramenta que utiliza técnicas de visão computacional para detectar monstros na Battle List do Tibia. O sistema captura a tela em tempo real e localiza templates de monstros usando Template Matching e ORB Feature Matching.

### ✨ Funcionalidades

- 🔍 **Detecção Multi-Escala**: Detecta monstros em diferentes tamanhos
- 🎯 **Seleção de ROI com Overlay**: Selecione a região diretamente sobre a tela do jogo
- ⚡ **Captura BitBlt**: Performance nativa do Windows (~1ms por captura)
- 🖱️ **Mover Mouse para Monstro**: Move o cursor para a posição do monstro detectado
- 📊 **Estatísticas em Tempo Real**: Taxa de detecção e confiança
- ⚙️ **Configurações Ajustáveis**: FPS, threshold, offset e pré-processamento

## 🚀 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- Windows 10/11

### Passos

1. Clone o repositório:
```bash
git clone https://github.com/NckLabs/monster_detector.git
cd monster_detector
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
```

3. Ative o ambiente virtual:
```bash
# Windows
venv\Scripts\activate
```

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

## 📦 Dependências

```
opencv-python>=4.8.0
opencv-contrib-python>=4.8.0
PyQt5>=5.15.0
numpy>=1.24.0
pywin32>=306
Pillow>=10.0.0
```

## 🎮 Como Usar

### 1. Executar o programa

```bash
python main.py
```

### 2. Carregar Template

- Clique em **"📁 Carregar Template"**
- Selecione a imagem do monstro (PNG recomendado)
- O template deve ser uma captura do ícone do monstro na Battle List

### 3. Selecionar ROI

- Clique em **"🎯 Selecionar ROI"**
- Uma película transparente cobrirá a tela
- Clique e arraste para selecionar a região da Battle List
- Solte o mouse para confirmar

### 4. Iniciar Detecção

- Clique em **"▶ Iniciar"** para começar a detecção em tempo real
- O sistema mostrará:
  - Visualização com retângulo verde ao redor do monstro
  - Cruz vermelha no ponto de clique
  - Confiança da detecção

### 5. Mover Mouse

- Quando um monstro for detectado, clique em **"🖱️ Mover Mouse para Monstro"**
- O cursor será movido para a posição do monstro

## ⚙️ Configurações

### Métodos de Detecção

| Opção | Descrição |
|-------|-----------|
| **Template Matching** | Busca por correspondência de padrões |
| **ORB Feature Matching** | Detecção por características visuais |
| **Pré-processamento Avançado** | Melhora contraste e reduz ruído |

### Parâmetros

| Parâmetro | Descrição | Padrão |
|-----------|-----------|--------|
| **FPS** | Taxa de detecção por segundo | 10 |
| **Threshold** | Confiança mínima para detecção | 65% |
| **Offset X/Y** | Ajuste fino da posição do clique | 0 |

## 📁 Estrutura do Projeto

```
monster_detector/
├── main.py              # Ponto de entrada
├── detector.py          # Motor de detecção (Template + ORB)
├── screen_capture.py    # Captura de tela (BitBlt + Overlay ROI)
├── ui.py                # Interface gráfica (PyQt5)
├── config.py            # Configurações globais
├── requirements.txt     # Dependências
└── templates/           # Templates de monstros
    ├── default/
    │   └── bug.png
    └── shiny/
        └── bug_shiny.png
```

## 🔧 Configurações Avançadas (config.py)

```python
# Escalas de detecção
SCALES = [0.0625, 0.125, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]

# Limiar de confiança
TEMPLATE_THRESHOLD = 0.65

# Pré-processamento
USE_PREPROCESSING_ENHANCEMENT = True
CLAHE_CLIP_LIMIT = 1.5

# Posição do mouse
USE_CENTER_POSITION = True  # Usa centro do template
POSITION_OFFSET_X = 0
POSITION_OFFSET_Y = 0

# Debug
DEBUG_CAPTURE_LOGS = True
SAVE_DEBUG_IMAGES = False
```

## 🐛 Solução de Problemas

### Detecção no fundo cinza

- Desative **"Pré-processamento Avançado"**
- Aumente o **Threshold** para 75-80%
- Verifique se o template está correto

### Posição do clique incorreta

- Ajuste os valores de **Offset X/Y**
- Verifique se **USE_CENTER_POSITION** está ativado

### Erro na captura de tela

- O sistema usa fallback automático para ImageGrab
- Verifique se o jogo está visível na tela

## 📄 Licença

Este projeto é apenas para fins educacionais. Use por sua conta e risco.

## 👤 Autor

**NckLabs** - [GitHub](https://github.com/NckLabs)

---

⭐ Se este projeto foi útil, deixe uma estrela no repositório!

