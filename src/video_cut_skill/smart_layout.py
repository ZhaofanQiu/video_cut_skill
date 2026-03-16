"""Smart layout and auto-composition system.

智能布局系统，支持自动构图、多画幅适配、人脸/主体检测。
"""

import json
import warnings
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# 尝试导入 OpenCV
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    warnings.warn("OpenCV not available, smart layout will be limited")

from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper


class AspectRatio(Enum):
    """画幅比例枚举."""
    PORTRAIT_9_16 = "9:16"      # 抖音/Instagram Reels
    PORTRAIT_4_5 = "4:5"        # Instagram Feed
    SQUARE_1_1 = "1:1"          # Instagram/Twitter
    LANDSCAPE_16_9 = "16:9"     # YouTube/标准视频
    LANDSCAPE_21_9 = "21:9"     # 电影宽屏
    LANDSCAPE_4_3 = "4:3"       # 经典视频
    
    @property
    def ratio(self) -> float:
        """获取比例数值."""
        ratios = {
            "9:16": 9/16,
            "4:5": 4/5,
            "1:1": 1.0,
            "16:9": 16/9,
            "21:9": 21/9,
            "4:3": 4/3
        }
        return ratios.get(self.value, 16/9)
    
    @classmethod
    def from_string(cls, ratio_str: str) -> "AspectRatio":
        """从字符串创建."""
        mapping = {
            "9:16": cls.PORTRAIT_9_16,
            "4:5": cls.PORTRAIT_4_5,
            "1:1": cls.SQUARE_1_1,
            "16:9": cls.LANDSCAPE_16_9,
            "21:9": cls.LANDSCAPE_21_9,
            "4:3": cls.LANDSCAPE_4_3
        }
        return mapping.get(ratio_str, cls.LANDSCAPE_16_9)


class CompositionRule(Enum):
    """构图规则枚举."""
    CENTER = "center"                    # 中心构图
    RULE_OF_THIRDS = "rule_of_thirds"    # 三分法
    GOLDEN_RATIO = "golden_ratio"        # 黄金分割
    SYMMETRY = "symmetry"                # 对称构图
    HEADROOM = "headroom"                # 头部空间
    EYE_LEVEL = "eye_level"              # 眼平线
    SAFE_AREA = "safe_area"              # 安全区域
    FACE_CENTER = "face_center"          # 人脸居中
    SUBJECT_CENTER = "subject_center"    # 主体居中


@dataclass
class FaceDetection:
    """人脸检测结果.
    
    Attributes:
        bbox: 边界框 (x, y, w, h)
        confidence: 检测置信度
        landmarks: 关键点 (可选)
    """
    bbox: Tuple[int, int, int, int]
    confidence: float
    landmarks: Optional[List[Tuple[int, int]]] = None
    
    @property
    def center(self) -> Tuple[float, float]:
        """边界框中心点."""
        x, y, w, h = self.bbox
        return (x + w / 2, y + h / 2)
    
    @property
    def area(self) -> int:
        """边界框面积."""
        _, _, w, h = self.bbox
        return w * h
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox,
            "center": self.center,
            "confidence": self.confidence,
            "area": self.area
        }


@dataclass
class SubjectDetection:
    """主体检测结果.
    
    Attributes:
        bbox: 边界框 (x, y, w, h)
        confidence: 检测置信度
        label: 标签（如 "person", "car" 等）
    """
    bbox: Tuple[int, int, int, int]
    confidence: float
    label: str = "subject"
    
    @property
    def center(self) -> Tuple[float, float]:
        """边界框中心点."""
        x, y, w, h = self.bbox
        return (x + w / 2, y + h / 2)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox,
            "center": self.center,
            "confidence": self.confidence,
            "label": self.label
        }


@dataclass
class CropRegion:
    """裁剪区域.
    
    Attributes:
        x: 左上角 x 坐标
        y: 左上角 y 坐标
        width: 宽度
        height: 高度
        confidence: 构图置信度
        rule_applied: 应用的构图规则
    """
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0
    rule_applied: CompositionRule = CompositionRule.CENTER
    
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """边界框格式."""
        return (self.x, self.y, self.width, self.height)
    
    @property
    def center(self) -> Tuple[float, float]:
        """中心点."""
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "center": self.center,
            "confidence": self.confidence,
            "rule_applied": self.rule_applied.value
        }


@dataclass
class LayoutSuggestion:
    """布局建议.
    
    Attributes:
        crop_region: 建议裁剪区域
        aspect_ratio: 目标画幅比例
        score: 构图评分 (0-100)
        reason: 建议原因
        safe_for_text: 是否适合叠加文字
    """
    crop_region: CropRegion
    aspect_ratio: AspectRatio
    score: float
    reason: str = ""
    safe_for_text: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "crop_region": self.crop_region.to_dict(),
            "aspect_ratio": self.aspect_ratio.value,
            "score": self.score,
            "reason": self.reason,
            "safe_for_text": self.safe_for_text
        }


class FaceDetector:
    """人脸检测器.
    
    检测视频中的人脸位置。
    
    Example:
        >>> detector = FaceDetector()
        >>> faces = detector.detect("video.mp4", time=5.0)
        >>>
        >>> for face in faces:
        ...     print(f"Face at: {face.center}")
    """
    
    def __init__(self, confidence_threshold: float = 0.7):
        """初始化人脸检测器.
        
        Args:
            confidence_threshold: 检测置信度阈值
        """
        self.confidence_threshold = confidence_threshold
        self._face_cascade = None
        
        if CV2_AVAILABLE:
            # 加载 OpenCV 人脸检测器
            try:
                self._face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                )
            except Exception:
                pass
    
    def detect(
        self,
        video_path: Union[str, Path],
        time: Optional[float] = None
    ) -> List[FaceDetection]:
        """检测人脸.
        
        Args:
            video_path: 视频文件路径
            time: 指定时间点（秒），None则取第一帧
            
        Returns:
            人脸检测结果列表
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if not CV2_AVAILABLE or self._face_cascade is None:
            return []
        
        # 提取帧
        frame = self._extract_frame(video_path, time or 0)
        
        if frame is None:
            return []
        
        # 转换为灰度
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 检测人脸
        detections = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        faces = []
        for (x, y, w, h) in detections:
            # OpenCV 返回的是 (x, y, w, h)
            faces.append(FaceDetection(
                bbox=(int(x), int(y), int(w), int(h)),
                confidence=0.8  # Haar 不提供置信度，使用固定值
            ))
        
        return faces
    
    def detect_multi_frame(
        self,
        video_path: Union[str, Path],
        num_frames: int = 5
    ) -> Dict[float, List[FaceDetection]]:
        """在多个时间点检测人脸.
        
        Args:
            video_path: 视频文件路径
            num_frames: 检测帧数
            
        Returns:
            时间点到检测结果的映射
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # 获取视频时长
        wrapper = FFmpegWrapper()
        info = wrapper.get_video_info(str(video_path))
        duration = info.get("duration", 0)
        
        if duration == 0:
            return {}
        
        # 均匀采样时间点
        times = np.linspace(0, duration, num_frames)
        
        results = {}
        for t in times:
            faces = self.detect(video_path, time=t)
            if faces:
                results[float(t)] = faces
        
        return results
    
    def get_main_face(
        self,
        video_path: Union[str, Path],
        time: Optional[float] = None
    ) -> Optional[FaceDetection]:
        """获取主要人脸（最大或最居中）.
        
        Args:
            video_path: 视频文件路径
            time: 指定时间点
            
        Returns:
            主要人脸，如果没有则返回 None
        """
        faces = self.detect(video_path, time)
        
        if not faces:
            return None
        
        # 返回最大的人脸
        return max(faces, key=lambda f: f.area)
    
    def _extract_frame(
        self,
        video_path: Path,
        time: float
    ) -> Optional[np.ndarray]:
        """提取视频帧."""
        if not CV2_AVAILABLE:
            return None
        
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            return None
        
        # 跳转到指定时间
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(time * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return frame
        
        return None


class SubjectDetector:
    """主体检测器.
    
    检测视频中的主要主体。
    
    Example:
        >>> detector = SubjectDetector()
        >>> subjects = detector.detect("video.mp4")
        >>>
        >>> for subject in subjects:
        ...     print(f"Subject: {subject.label} at {subject.center}")
    """
    
    def __init__(self, confidence_threshold: float = 0.5):
        """初始化主体检测器.
        
        Args:
            confidence_threshold: 检测置信度阈值
        """
        self.confidence_threshold = confidence_threshold
    
    def detect(
        self,
        video_path: Union[str, Path],
        time: Optional[float] = None
    ) -> List[SubjectDetection]:
        """检测主体.
        
        Args:
            video_path: 视频文件路径
            time: 指定时间点
            
        Returns:
            主体检测结果列表
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # 基础实现：使用帧差异检测运动主体
        # 实际应用可以使用深度学习检测器如 YOLO
        
        if not CV2_AVAILABLE:
            return []
        
        # 提取帧
        cap = cv2.VideoCapture(str(video_path))
        
        if time is not None:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_number = int(time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return []
        
        # 简单的边缘检测来估计主体位置
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        
        # 查找轮廓
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        subjects = []
        height, width = frame.shape[:2]
        
        for contour in contours:
            area = cv2.contourArea(contour)
            # 过滤小轮廓
            if area > (width * height * 0.01):  # 大于画面 1%
                x, y, w, h = cv2.boundingRect(contour)
                subjects.append(SubjectDetection(
                    bbox=(x, y, w, h),
                    confidence=min(area / (width * height * 0.1), 1.0),
                    label="subject"
                ))
        
        # 按面积排序
        subjects.sort(key=lambda s: s.bbox[2] * s.bbox[3], reverse=True)
        
        return subjects[:5]  # 返回前5个
    
    def get_main_subject(
        self,
        video_path: Union[str, Path],
        time: Optional[float] = None
    ) -> Optional[SubjectDetection]:
        """获取主要主体.
        
        Args:
            video_path: 视频文件路径
            time: 指定时间点
            
        Returns:
            主要主体，如果没有则返回 None
        """
        subjects = self.detect(video_path, time)
        
        if not subjects:
            return None
        
        return subjects[0]


class CompositionEngine:
    """构图引擎.
    
    基于构图规则计算最佳裁剪区域。
    
    Example:
        >>> engine = CompositionEngine()
        >>>
        >>> # 基于人脸构图
        >>> crop = engine.compute_crop(
        ...     video_width=1920,
        ...     video_height=1080,
        ...     target_ratio=AspectRatio.PORTRAIT_9_16,
        ...     faces=[face1, face2],
        ...     rule=CompositionRule.FACE_CENTER
        ... )
        >>>
        >>> print(f"Crop at: {crop.x}, {crop.y}, {crop.width}, {crop.height}")
    """
    
    def __init__(self):
        """初始化构图引擎."""
        self.rules = {
            CompositionRule.CENTER: self._apply_center_rule,
            CompositionRule.RULE_OF_THIRDS: self._apply_rule_of_thirds,
            CompositionRule.GOLDEN_RATIO: self._apply_golden_ratio,
            CompositionRule.SYMMETRY: self._apply_symmetry_rule,
            CompositionRule.HEADROOM: self._apply_headroom_rule,
            CompositionRule.FACE_CENTER: self._apply_face_center_rule,
            CompositionRule.SUBJECT_CENTER: self._apply_subject_center_rule,
        }
    
    def compute_crop(
        self,
        video_width: int,
        video_height: int,
        target_ratio: AspectRatio,
        faces: Optional[List[FaceDetection]] = None,
        subjects: Optional[List[SubjectDetection]] = None,
        rule: CompositionRule = CompositionRule.FACE_CENTER,
        safe_margin: float = 0.1
    ) -> CropRegion:
        """计算裁剪区域.
        
        Args:
            video_width: 视频宽度
            video_height: 视频高度
            target_ratio: 目标画幅比例
            faces: 人脸检测结果
            subjects: 主体检测结果
            rule: 构图规则
            safe_margin: 安全边距（相对值）
            
        Returns:
            裁剪区域
        """
        # 计算目标尺寸
        target_ratio_value = target_ratio.ratio
        current_ratio = video_width / video_height
        
        if current_ratio > target_ratio_value:
            # 视频更宽，基于高度计算宽度
            crop_height = video_height
            crop_width = int(video_height * target_ratio_value)
        else:
            # 视频更高，基于宽度计算高度
            crop_width = video_width
            crop_height = int(video_width / target_ratio_value)
        
        # 应用构图规则
        if rule in self.rules:
            x, y = self.rules[rule](
                video_width, video_height,
                crop_width, crop_height,
                faces, subjects
            )
        else:
            # 默认居中
            x = (video_width - crop_width) // 2
            y = (video_height - crop_height) // 2
        
        # 确保不超出边界
        x = max(0, min(x, video_width - crop_width))
        y = max(0, min(y, video_height - crop_height))
        
        # 应用安全边距
        margin_x = int(crop_width * safe_margin)
        margin_y = int(crop_height * safe_margin)
        
        # 重新调整以确保安全区域
        x = max(margin_x, min(x, video_width - crop_width - margin_x))
        y = max(margin_y, min(y, video_height - crop_height - margin_y))
        
        return CropRegion(
            x=x,
            y=y,
            width=crop_width,
            height=crop_height,
            confidence=self._calculate_confidence(faces, subjects, rule),
            rule_applied=rule
        )
    
    def suggest_layouts(
        self,
        video_width: int,
        video_height: int,
        faces: Optional[List[FaceDetection]] = None,
        subjects: Optional[List[SubjectDetection]] = None
    ) -> List[LayoutSuggestion]:
        """建议多种布局.
        
        Args:
            video_width: 视频宽度
            video_height: 视频高度
            faces: 人脸检测结果
            subjects: 主体检测结果
            
        Returns:
            布局建议列表
        """
        suggestions = []
        
        # 为不同画幅比例生成建议
        ratios = [
            AspectRatio.PORTRAIT_9_16,
            AspectRatio.SQUARE_1_1,
            AspectRatio.LANDSCAPE_16_9
        ]
        
        rules = [
            CompositionRule.FACE_CENTER,
            CompositionRule.RULE_OF_THIRDS,
            CompositionRule.CENTER
        ]
        
        for ratio in ratios:
            for rule in rules:
                crop = self.compute_crop(
                    video_width, video_height, ratio,
                    faces, subjects, rule
                )
                
                # 评分
                score = self._score_composition(crop, faces, subjects)
                
                suggestions.append(LayoutSuggestion(
                    crop_region=crop,
                    aspect_ratio=ratio,
                    score=score,
                    reason=f"{rule.value} for {ratio.value}",
                    safe_for_text=self._is_safe_for_text(crop)
                ))
        
        # 按评分排序
        suggestions.sort(key=lambda s: s.score, reverse=True)
        
        return suggestions[:5]  # 返回前5个
    
    def _apply_center_rule(
        self,
        video_w: int, video_h: int,
        crop_w: int, crop_h: int,
        faces: Optional[List[FaceDetection]],
        subjects: Optional[List[SubjectDetection]]
    ) -> Tuple[int, int]:
        """应用中心构图."""
        x = (video_w - crop_w) // 2
        y = (video_h - crop_h) // 2
        return x, y
    
    def _apply_rule_of_thirds(
        self,
        video_w: int, video_h: int,
        crop_w: int, crop_h: int,
        faces: Optional[List[FaceDetection]],
        subjects: Optional[List[SubjectDetection]]
    ) -> Tuple[int, int]:
        """应用三分法."""
        # 计算画面三分线交点
        if faces:
            # 将人脸放在交点附近
            face = faces[0]
            fx, fy = face.center
            
            # 选择最近的交点
            third_x = video_w / 3
            third_y = video_h / 3
            
            # 计算到四个交点的距离
            intersections = [
                (third_x, third_y),
                (2 * third_x, third_y),
                (third_x, 2 * third_y),
                (2 * third_x, 2 * third_y)
            ]
            
            best_x, best_y = min(
                intersections,
                key=lambda p: (p[0] - fx) ** 2 + (p[1] - fy) ** 2
            )
            
            x = int(best_x - crop_w / 2)
            y = int(best_y - crop_h / 2)
        else:
            # 默认居中
            x = (video_w - crop_w) // 2
            y = (video_h - crop_h) // 2
        
        return x, y
    
    def _apply_golden_ratio(
        self,
        video_w: int, video_h: int,
        crop_w: int, crop_h: int,
        faces: Optional[List[FaceDetection]],
        subjects: Optional[List[SubjectDetection]]
    ) -> Tuple[int, int]:
        """应用黄金分割."""
        phi = 0.618  # 黄金比例
        
        if faces:
            face = faces[0]
            fx, fy = face.center
            
            # 将人脸放在黄金分割点
            x = int(fx - crop_w * phi)
            y = int(fy - crop_h * phi)
        else:
            x = int((video_w - crop_w) * phi)
            y = int((video_h - crop_h) * phi)
        
        return x, y
    
    def _apply_symmetry_rule(
        self,
        video_w: int, video_h: int,
        crop_w: int, crop_h: int,
        faces: Optional[List[FaceDetection]],
        subjects: Optional[List[SubjectDetection]]
    ) -> Tuple[int, int]:
        """应用对称构图."""
        # 对称构图通常居中
        return self._apply_center_rule(video_w, video_h, crop_w, crop_h, faces, subjects)
    
    def _apply_headroom_rule(
        self,
        video_w: int, video_h: int,
        crop_w: int, crop_h: int,
        faces: Optional[List[FaceDetection]],
        subjects: Optional[List[SubjectDetection]]
    ) -> Tuple[int, int]:
        """应用头部空间规则."""
        x = (video_w - crop_w) // 2
        
        if faces:
            # 确保人脸顶部有适当空间（20-30%）
            face = faces[0]
            _, fy, _, fh = face.bbox
            
            # 人脸应该在画面上方 1/3 处
            y = int(fy + fh * 0.3 - crop_h * 0.3)
        else:
            y = (video_h - crop_h) // 2
        
        return x, y
    
    def _apply_face_center_rule(
        self,
        video_w: int, video_h: int,
        crop_w: int, crop_h: int,
        faces: Optional[List[FaceDetection]],
        subjects: Optional[List[SubjectDetection]]
    ) -> Tuple[int, int]:
        """应用人脸居中规则."""
        if faces:
            # 计算人脸中心
            if len(faces) == 1:
                fx, fy = faces[0].center
            else:
                # 多个人脸，取平均中心
                avg_x = sum(f.center[0] for f in faces) / len(faces)
                avg_y = sum(f.center[1] for f in faces) / len(faces)
                fx, fy = avg_x, avg_y
            
            x = int(fx - crop_w / 2)
            y = int(fy - crop_h / 2)
        else:
            # 没有人脸，居中
            x = (video_w - crop_w) // 2
            y = (video_h - crop_h) // 2
        
        return x, y
    
    def _apply_subject_center_rule(
        self,
        video_w: int, video_h: int,
        crop_w: int, crop_h: int,
        faces: Optional[List[FaceDetection]],
        subjects: Optional[List[SubjectDetection]]
    ) -> Tuple[int, int]:
        """应用主体居中规则."""
        if subjects:
            subject = subjects[0]
            sx, sy = subject.center
            
            x = int(sx - crop_w / 2)
            y = int(sy - crop_h / 2)
        elif faces:
            # 回退到人脸
            return self._apply_face_center_rule(
                video_w, video_h, crop_w, crop_h, faces, subjects
            )
        else:
            x = (video_w - crop_w) // 2
            y = (video_h - crop_h) // 2
        
        return x, y
    
    def _calculate_confidence(
        self,
        faces: Optional[List[FaceDetection]],
        subjects: Optional[List[SubjectDetection]],
        rule: CompositionRule
    ) -> float:
        """计算构图置信度."""
        confidence = 0.5
        
        if faces:
            # 人脸检测提升置信度
            avg_conf = sum(f.confidence for f in faces) / len(faces)
            confidence += avg_conf * 0.3
        
        if subjects:
            # 主体检测提升置信度
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _score_composition(
        self,
        crop: CropRegion,
        faces: Optional[List[FaceDetection]],
        subjects: Optional[List[SubjectDetection]]
    ) -> float:
        """评分构图质量."""
        score = 50.0  # 基础分
        
        # 根据检测质量加分
        if faces:
            score += 20
            # 检查人脸是否在裁剪区域内
            for face in faces:
                fx, fy = face.center
                if (crop.x <= fx <= crop.x + crop.width and
                    crop.y <= fy <= crop.y + crop.height):
                    score += 10
                    break
        
        if subjects:
            score += 10
        
        return min(score, 100.0)
    
    def _is_safe_for_text(self, crop: CropRegion) -> bool:
        """检查是否适合叠加文字."""
        # 简单的启发式：检查底部区域是否干净
        # 实际应用可以分析该区域的复杂度
        return True


class SmartLayoutEditor:
    """智能布局编辑器.
    
    将智能布局集成到视频编辑流程。
    
    Example:
        >>> editor = SmartLayoutEditor()
        >>>
        >>> # 分析并建议最佳布局
        >>> suggestions = editor.analyze("video.mp4")
        >>> for suggestion in suggestions:
        ...     print(f"{suggestion.aspect_ratio.value}: score {suggestion.score}")
        >>>
        >>> # 自动裁剪为 9:16
        >>> editor.auto_crop(
        ...     "input.mp4",
        ...     "output.mp4",
        ...     aspect_ratio=AspectRatio.PORTRAIT_9_16
        ... )
    """
    
    def __init__(
        self,
        face_detector: Optional[FaceDetector] = None,
        subject_detector: Optional[SubjectDetector] = None,
        composition_engine: Optional[CompositionEngine] = None
    ):
        """初始化智能布局编辑器.
        
        Args:
            face_detector: 人脸检测器
            subject_detector: 主体检测器
            composition_engine: 构图引擎
        """
        self.face_detector = face_detector or FaceDetector()
        self.subject_detector = subject_detector or SubjectDetector()
        self.composition_engine = composition_engine or CompositionEngine()
        
        self._last_suggestions: Optional[List[LayoutSuggestion]] = None
        self._video_info: Optional[Dict[str, Any]] = None
    
    def analyze(
        self,
        video_path: Union[str, Path],
        num_sample_frames: int = 3
    ) -> List[LayoutSuggestion]:
        """分析视频并建议布局.
        
        Args:
            video_path: 视频文件路径
            num_sample_frames: 采样帧数
            
        Returns:
            布局建议列表
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # 获取视频信息
        wrapper = FFmpegWrapper()
        self._video_info = wrapper.get_video_info(str(video_path))
        
        video_width = self._video_info.get("width", 1920)
        video_height = self._video_info.get("height", 1080)
        
        # 在多个时间点检测
        duration = self._video_info.get("duration", 0)
        times = np.linspace(0, duration, num_sample_frames) if duration > 0 else [0]
        
        all_faces = []
        all_subjects = []
        
        for t in times:
            faces = self.face_detector.detect(video_path, time=t)
            subjects = self.subject_detector.detect(video_path, time=t)
            
            all_faces.extend(faces)
            all_subjects.extend(subjects)
        
        # 生成布局建议
        self._last_suggestions = self.composition_engine.suggest_layouts(
            video_width, video_height,
            all_faces if all_faces else None,
            all_subjects if all_subjects else None
        )
        
        return self._last_suggestions
    
    def auto_crop(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        aspect_ratio: AspectRatio,
        rule: CompositionRule = CompositionRule.FACE_CENTER
    ) -> str:
        """自动裁剪视频.
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            aspect_ratio: 目标画幅比例
            rule: 构图规则
            
        Returns:
            输出文件路径
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # 获取视频信息
        wrapper = FFmpegWrapper()
        info = wrapper.get_video_info(str(video_path))
        
        video_width = info.get("width", 1920)
        video_height = info.get("height", 1080)
        
        # 检测人脸和主体
        faces = self.face_detector.detect(video_path)
        subjects = self.subject_detector.detect(video_path)
        
        # 计算裁剪区域
        crop = self.composition_engine.compute_crop(
            video_width, video_height,
            aspect_ratio,
            faces if faces else None,
            subjects if subjects else None,
            rule
        )
        
        # 执行裁剪
        wrapper.crop_video(
            str(video_path),
            str(output_path),
            crop.x, crop.y,
            crop.width, crop.height
        )
        
        return str(output_path)
    
    def smart_reframe(
        self,
        video_path: Union[str, Path],
        output_path: Union[str, Path],
        target_aspect_ratio: AspectRatio,
        smooth_motion: bool = True
    ) -> str:
        """智能重构图（动态跟踪主体）.
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            target_aspect_ratio: 目标画幅比例
            smooth_motion: 是否平滑运动
            
        Returns:
            输出文件路径
        """
        # 这是一个高级功能，需要跟踪主体运动
        # 基础实现：使用静态裁剪
        return self.auto_crop(video_path, output_path, target_aspect_ratio)
    
    def batch_crop_for_platforms(
        self,
        video_path: Union[str, Path],
        output_dir: Union[str, Path]
    ) -> Dict[str, str]:
        """批量生成不同平台的版本.
        
        Args:
            video_path: 输入视频路径
            output_dir: 输出目录
            
        Returns:
            平台到输出路径的映射
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        platforms = {
            "tiktok": AspectRatio.PORTRAIT_9_16,
            "instagram": AspectRatio.SQUARE_1_1,
            "youtube": AspectRatio.LANDSCAPE_16_9,
            "youtube_shorts": AspectRatio.PORTRAIT_9_16
        }
        
        results = {}
        
        for platform, ratio in platforms.items():
            output_path = output_dir / f"{platform}_{video_path.stem}.mp4"
            try:
                self.auto_crop(video_path, output_path, ratio)
                results[platform] = str(output_path)
            except Exception as e:
                print(f"Failed to generate {platform} version: {e}")
        
        return results
    
    def get_best_layout_for_text_overlay(
        self,
        text_position: str = "bottom"
    ) -> Optional[LayoutSuggestion]:
        """获取适合叠加文字的最佳布局.
        
        Args:
            text_position: 文字位置 ("top", "bottom", "center")
            
        Returns:
            最佳布局建议
        """
        if not self._last_suggestions:
            return None
        
        # 筛选适合叠加文字的布局
        suitable = [s for s in self._last_suggestions if s.safe_for_text]
        
        if not suitable:
            return None
        
        return suitable[0]
    
    def export_crop_metadata(
        self,
        output_path: Union[str, Path]
    ) -> None:
        """导出裁剪元数据.
        
        Args:
            output_path: 输出文件路径
        """
        if not self._last_suggestions:
            raise ValueError("No analysis result. Call analyze() first.")
        
        data = {
            "video_info": self._video_info,
            "suggestions": [s.to_dict() for s in self._last_suggestions]
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# 便捷函数

def auto_crop_video(
    video_path: Union[str, Path],
    output_path: Union[str, Path],
    aspect_ratio: Union[str, AspectRatio] = "9:16"
) -> str:
    """便捷函数：自动裁剪视频.
    
    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        aspect_ratio: 目标画幅比例
        
    Returns:
        输出文件路径
    """
    if isinstance(aspect_ratio, str):
        aspect_ratio = AspectRatio.from_string(aspect_ratio)
    
    editor = SmartLayoutEditor()
    return editor.auto_crop(video_path, output_path, aspect_ratio)


def suggest_video_layouts(
    video_path: Union[str, Path]
) -> List[LayoutSuggestion]:
    """便捷函数：建议视频布局.
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        布局建议列表
    """
    editor = SmartLayoutEditor()
    return editor.analyze(video_path)
