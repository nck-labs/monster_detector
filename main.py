"""
Sistema de Detecção Multi-Escala de Monstros
Versão: 1.0.0 - Real-Time ROI Edition
Autor: NckLabs

Detecção em tempo real usando BitBlt para máxima performance
"""

if __name__ == '__main__':
    from ui import main
    main()




"""
1. **✅ Captura BitBlt**: Performance nativa do Windows
2. **✅ Seleção ROI Interativa**: 2 cliques do mouse
3. **✅ Detecção em Tempo Real**: Thread assíncrona
4. **✅ FPS Configurável**: 1-60 FPS
5. **✅ Estatísticas Live**: Taxa de sucesso em tempo real
6. **✅ Zero I/O de Disco**: Tudo em memória (numpy)
7. **✅ Preview ao Vivo**: Visualização contínua

## 📦 Dependências Atualizadas
```bash
pip install opencv-python opencv-contrib-python PyQt5 numpy pywin32 pillow
```

## 🚀 Workflow

1. **Carregar Template** → Imagem do monstro
2. **Selecionar ROI** → 2 cliques na tela
3. **Iniciar** → Detecção contínua
4. **Monitorar** → Visualização + estatísticas

## ⚡ Performance

- **BitBlt**: ~1ms por captura
- **Detecção**: 10-60 FPS configurável
- **Memória**: ~50MB (sem I/O)

Sistema pronto para **automação de alta escala**! 🚀"""