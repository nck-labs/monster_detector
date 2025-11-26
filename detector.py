"""
Motor de detecção multi-escala com Template Matching e ORB
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from pathlib import Path
import config


@dataclass
class DetectionResult:
    """Resultado da detecção"""
    found: bool
    confidence: float
    scale: float
    position: Tuple[int, int]  # (x, y)
    size: Tuple[int, int]      # (width, height)
    method: str                 # 'template' ou 'orb'
    
    def __str__(self):
        if not self.found:
            return "Nenhum monstro detectado"
        return (f"Monstro detectado | Método: {self.method} | "
                f"Confiança: {self.confidence:.2%} | "
                f"Escala: {self.scale:.2f}x | "
                f"Posição: {self.position} | "
                f"Tamanho: {self.size}")


class MonsterDetector:
    """
    Detector de monstros com suporte multi-escala usando Template Matching e ORB
    """
    
    def __init__(self, template_path: str):
        """
        Inicializa o detector
        
        Args:
            template_path: Caminho para a imagem template do monstro
        """
        # Carrega template com suporte a transparência
        self.template_original = self._load_template(template_path)
        if self.template_original is None:
            raise FileNotFoundError(f"Template não encontrado: {template_path}")
        
        # Pré-processa template
        self.template_processed = self._preprocess_image(self.template_original)
        
        # Inicializa detector ORB
        self.orb = cv2.ORB_create(nfeatures=config.ORB_FEATURES)
        self.bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        # Extrai features ORB do template
        self.template_keypoints, self.template_descriptors = self.orb.detectAndCompute(
            self.template_processed, None
        )
        
        print(f"✓ Template carregado: {Path(template_path).name}")
        print(f"✓ Dimensões: {self.template_original.shape[:2]}")
        print(f"✓ Features ORB extraídas: {len(self.template_keypoints)}")
    
    def _load_template(self, template_path: str) -> np.ndarray:
        """
        Carrega template com suporte a transparência (PNG com alpha)
        
        Args:
            template_path: Caminho para o template
            
        Returns:
            Imagem BGR (sem canal alpha)
        """
        # Tenta carregar com cv2 primeiro
        img = cv2.imread(template_path, cv2.IMREAD_COLOR)
        
        if img is not None:
            # Se carregou, verifica se tem 4 canais (BGR + Alpha)
            if len(img.shape) == 3 and img.shape[2] == 4:
                # Remove canal alpha e compõe com fundo branco
                b, g, r, a = cv2.split(img)
                alpha = a.astype(np.float32) / 255.0
                
                # Composição com fundo branco
                img_bgr = cv2.merge([b, g, r])
                white_bg = np.ones_like(img_bgr) * 255
                img = (img_bgr * alpha[:, :, np.newaxis] + 
                       white_bg * (1 - alpha[:, :, np.newaxis])).astype(np.uint8)
            return img
        
        # Fallback: tenta com PIL para PNG com transparência
        try:
            from PIL import Image
            pil_img = Image.open(template_path)
            
            # Converte RGBA para RGB com fundo branco
            if pil_img.mode == 'RGBA':
                rgb_img = Image.new('RGB', pil_img.size, (255, 255, 255))
                rgb_img.paste(pil_img, mask=pil_img.split()[3])  # Usa canal alpha como máscara
                pil_img = rgb_img
            elif pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            
            # Converte PIL para numpy array BGR
            img_array = np.array(pil_img)
            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            return img
        except Exception as e:
            print(f"⚠ Erro ao carregar template com PIL: {e}")
            return None
    
    def _preprocess_image(self, image: np.ndarray, use_enhancement: bool = None) -> np.ndarray:
        """
        Pré-processa imagem para melhorar detecção
        
        Args:
            image: Imagem BGR
            use_enhancement: Se None, usa config.USE_PREPROCESSING_ENHANCEMENT
            
        Returns:
            Imagem processada em escala de cinza
        """
        # Converte para escala de cinza
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Verifica se deve usar processamento completo ou simples
        use_full = getattr(config, 'USE_PREPROCESSING_ENHANCEMENT', True)
        if use_enhancement is not None:
            use_full = use_enhancement
        
        if not use_full:
            # Processamento simples - apenas escala de cinza
            return gray
        
        # Processamento completo
        # Aplica filtro bilateral (preserva bordas, reduz ruído)
        denoised = cv2.bilateralFilter(
            gray,
            config.BILATERAL_D,
            config.BILATERAL_SIGMA_COLOR,
            config.BILATERAL_SIGMA_SPACE
        )
        
        # Equalização de histograma adaptativa (CLAHE) - mais suave
        clahe = cv2.createCLAHE(
            clipLimit=getattr(config, 'CLAHE_CLIP_LIMIT', 1.5), 
            tileGridSize=(8, 8)
        )
        enhanced = clahe.apply(denoised)
        
        return enhanced
    
    def _template_matching_multiscale(
        self,
        battle_scene: np.ndarray
    ) -> Optional[DetectionResult]:
        """
        Template Matching em múltiplas escalas
        
        Args:
            battle_scene: Imagem da cena de batalha
            
        Returns:
            Melhor resultado encontrado ou None
        """
        best_result = None
        best_confidence = 0
        
        # Processa cena com o mesmo método usado no template
        scene_processed = self._preprocess_image(
            battle_scene, 
            use_enhancement=getattr(config, 'USE_PREPROCESSING_ENHANCEMENT', True)
        )
        h, w = self.template_processed.shape[:2]
        
        # Debug: salva imagens processadas se habilitado
        if getattr(config, 'SAVE_DEBUG_IMAGES', False):
            try:
                cv2.imwrite('debug_template_processed.png', self.template_processed)
                cv2.imwrite('debug_scene_processed.png', scene_processed)
            except:
                pass
        
        for scale in config.SCALES:
            # Redimensiona template
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # Ignora escalas muito pequenas ou muito grandes
            if new_w < 8 or new_h < 8 or new_w > scene_processed.shape[1] or new_h > scene_processed.shape[0]:
                continue
            
            resized_template = cv2.resize(
                self.template_processed,
                (new_w, new_h),
                interpolation=cv2.INTER_CUBIC
            )
            
            # Template matching - tenta múltiplos métodos e escolhe o melhor
            methods = [
                cv2.TM_CCOEFF_NORMED,
                cv2.TM_CCORR_NORMED,
            ]
            
            best_match_val = 0
            best_match_loc = None
            best_method = cv2.TM_CCOEFF_NORMED
            
            for method in methods:
                result = cv2.matchTemplate(
                    scene_processed,
                    resized_template,
                    method
                )
                
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # Para TM_CCOEFF_NORMED e TM_CCORR_NORMED, maior é melhor
                if max_val > best_match_val:
                    best_match_val = max_val
                    best_match_loc = max_loc
                    best_method = method
            
            max_val = best_match_val
            max_loc = best_match_loc
            
            # Atualiza melhor resultado
            if max_val > best_confidence:
                if max_val >= config.TEMPLATE_THRESHOLD:
                    best_confidence = max_val
                    
                    # Calcula posição (centro ou canto superior esquerdo)
                    if getattr(config, 'USE_CENTER_POSITION', True):
                        # Posição do centro do template
                        center_x = max_loc[0] + new_w // 2
                        center_y = max_loc[1] + new_h // 2
                        position = (center_x, center_y)
                    else:
                        # Posição do canto superior esquerdo
                        position = max_loc
                    
                    best_result = DetectionResult(
                        found=True,
                        confidence=max_val,
                        scale=scale,
                        position=position,
                        size=(new_w, new_h),
                        method='template'
                    )
                elif getattr(config, 'DEBUG_CAPTURE_LOGS', False) and max_val > 0.5:
                    # Log de detecções abaixo do threshold para debug
                    print(f"⚠ Detecção abaixo do threshold: {max_val:.2%} (threshold: {config.TEMPLATE_THRESHOLD:.2%}) na escala {scale:.2f}x")
        
        return best_result
    
    def _orb_matching(
        self,
        battle_scene: np.ndarray
    ) -> Optional[DetectionResult]:
        """
        Detecção usando ORB features
        
        Args:
            battle_scene: Imagem da cena de batalha
            
        Returns:
            Resultado da detecção ou None
        """
        scene_processed = self._preprocess_image(battle_scene)
        
        # Detecta features na cena
        scene_keypoints, scene_descriptors = self.orb.detectAndCompute(
            scene_processed, None
        )
        
        if scene_descriptors is None or len(scene_keypoints) < config.ORB_MIN_MATCHES:
            return None
        
        # Match features
        try:
            matches = self.bf_matcher.match(
                self.template_descriptors,
                scene_descriptors
            )
            matches = sorted(matches, key=lambda x: x.distance)
        except cv2.error:
            return None
        
        if len(matches) < config.ORB_MIN_MATCHES:
            return None
        
        # Extrai pontos correspondentes
        template_points = np.float32([
            self.template_keypoints[m.queryIdx].pt for m in matches
        ]).reshape(-1, 1, 2)
        
        scene_points = np.float32([
            scene_keypoints[m.trainIdx].pt for m in matches
        ]).reshape(-1, 1, 2)
        
        # Calcula homografia
        try:
            M, mask = cv2.findHomography(
                template_points,
                scene_points,
                cv2.RANSAC,
                5.0
            )
        except cv2.error:
            return None
        
        if M is None:
            return None
        
        # Calcula pontos transformados do template
        h, w = self.template_processed.shape[:2]
        corners = np.float32([
            [0, 0],
            [w, 0],
            [w, h],
            [0, h]
        ]).reshape(-1, 1, 2)
        
        transformed_corners = cv2.perspectiveTransform(corners, M)
        
        # Calcula bounding box
        x_coords = transformed_corners[:, 0, 0]
        y_coords = transformed_corners[:, 0, 1]
        
        x_min, x_max = int(np.min(x_coords)), int(np.max(x_coords))
        y_min, y_max = int(np.min(y_coords)), int(np.max(y_coords))
        
        detected_w = x_max - x_min
        detected_h = y_max - y_min
        
        # Calcula escala baseada na mudança de tamanho
        scale_x = detected_w / w
        scale_y = detected_h / h
        avg_scale = (scale_x + scale_y) / 2
        
        # Calcula posição (centro ou canto superior esquerdo)
        if getattr(config, 'USE_CENTER_POSITION', True):
            # Posição do centro do bounding box
            center_x = (x_min + x_max) // 2
            center_y = (y_min + y_max) // 2
            position = (center_x, center_y)
        else:
            # Posição do canto superior esquerdo
            position = (x_min, y_min)
        
        # Confiança baseada em inliers
        inliers = np.sum(mask)
        confidence = inliers / len(matches)
        
        return DetectionResult(
            found=True,
            confidence=confidence,
            scale=avg_scale,
            position=position,
            size=(detected_w, detected_h),
            method='orb'
        )
    
    def detect(
        self,
        battle_scene: np.ndarray,
        use_template: bool = True,
        use_orb: bool = True
    ) -> DetectionResult:
        """
        Detecta monstro na cena de batalha
        
        Args:
            battle_scene: Imagem da cena de batalha
            use_template: Usar Template Matching
            use_orb: Usar ORB matching
            
        Returns:
            Melhor resultado encontrado
        """
        results = []
        
        # Template Matching
        if use_template:
            template_result = self._template_matching_multiscale(battle_scene)
            if template_result:
                results.append(template_result)
        
        # ORB Matching
        if use_orb:
            orb_result = self._orb_matching(battle_scene)
            if orb_result:
                results.append(orb_result)
        
        # Retorna melhor resultado
        if not results:
            return DetectionResult(
                found=False,
                confidence=0.0,
                scale=0.0,
                position=(0, 0),
                size=(0, 0),
                method='none'
            )
        
        return max(results, key=lambda r: r.confidence)
    
    def visualize_detection(
        self,
        battle_scene: np.ndarray,
        result: DetectionResult
    ) -> np.ndarray:
        """
        Visualiza resultado da detecção
        
        Args:
            battle_scene: Imagem original
            result: Resultado da detecção
            
        Returns:
            Imagem com visualização
        """
        vis_image = battle_scene.copy()
        
        if not result.found:
            return vis_image
        
        x, y = result.position
        w, h = result.size
        
        # Se a posição é o centro, ajusta para desenhar o retângulo corretamente
        if getattr(config, 'USE_CENTER_POSITION', True):
            # A posição é o centro, então calcula o canto superior esquerdo
            rect_x = x - w // 2
            rect_y = y - h // 2
        else:
            # A posição já é o canto superior esquerdo
            rect_x = x
            rect_y = y
        
        # Desenha retângulo
        color = (0, 255, 0) if result.confidence > 0.8 else (0, 255, 255)
        cv2.rectangle(vis_image, (rect_x, rect_y), (rect_x + w, rect_y + h), color, 2)
        
        # Desenha cruz no centro do template (ponto de clique)
        center_color = (255, 0, 0)  # Vermelho para destacar
        cross_size = 5
        cv2.line(vis_image, (x - cross_size, y), (x + cross_size, y), center_color, 2)
        cv2.line(vis_image, (x, y - cross_size), (x, y + cross_size), center_color, 2)
        cv2.circle(vis_image, (x, y), 3, center_color, -1)  # Ponto central
        
        # Adiciona texto
        label = f"{result.method.upper()} {result.confidence:.1%}"
        cv2.putText(
            vis_image,
            label,
            (rect_x, rect_y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2
        )
        
        # Adiciona coordenadas do ponto de clique
        coord_text = f"({x}, {y})"
        cv2.putText(
            vis_image,
            coord_text,
            (x + 5, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            center_color,
            1
        )
        
        return vis_image