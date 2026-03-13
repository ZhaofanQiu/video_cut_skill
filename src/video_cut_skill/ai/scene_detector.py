"""Scene detection module using PySceneDetect."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from scenedetect import AdaptiveDetector, ContentDetector, ThresholdDetector, detect
from scenedetect.video_splitter import split_video_ffmpeg

logger = logging.getLogger(__name__)


@dataclass
class Scene:
    """场景/镜头片段."""

    start: float
    end: float
    start_frame: int
    end_frame: int

    @property
    def duration(self) -> float:
        """场景时长."""
        return self.end - self.start

    @property
    def frame_count(self) -> int:
        """帧数."""
        return self.end_frame - self.start_frame


@dataclass
class SceneDetectionResult:
    """场景检测结果."""

    scenes: List[Scene]
    video_path: str
    detector_type: str
    total_duration: float

    @property
    def scene_count(self) -> int:
        """场景数量."""
        return len(self.scenes)

    def get_scene_at_time(self, time: float) -> Optional[Scene]:
        """获取指定时间所在的场景."""
        for scene in self.scenes:
            if scene.start <= time <= scene.end:
                return scene
        return None

    def get_longest_scenes(self, n: int = 5) -> List[Scene]:
        """获取最长的 N 个场景."""
        return sorted(self.scenes, key=lambda s: s.duration, reverse=True)[:n]


class SceneDetector:
    """场景检测器.

    基于 PySceneDetect 实现.
    """

    DETECTOR_TYPES = {
        "content": ContentDetector,
        "threshold": ThresholdDetector,
        "adaptive": AdaptiveDetector,
    }

    def __init__(self, detector_type: str = "content"):
        """初始化场景检测器.

        Args:
            detector_type: 检测器类型 (content/threshold/adaptive)
        """
        if detector_type not in self.DETECTOR_TYPES:
            raise ValueError(
                f"Invalid detector type: {detector_type}. "
                f"Choose from: {list(self.DETECTOR_TYPES.keys())}"
            )

        self.detector_type = detector_type
        self._detector_class = self.DETECTOR_TYPES[detector_type]
        logger.info(f"SceneDetector initialized with {detector_type} detector")

    def detect(
        self,
        video_path: Union[str, Path],
        threshold: float = 27.0,
        min_scene_len: float = 0.5,  # 最小场景长度（秒）
        show_progress: bool = False,
    ) -> SceneDetectionResult:
        """检测视频场景.

        Args:
            video_path: 视频路径
            threshold: 检测阈值
            min_scene_len: 最小场景长度（秒）
            show_progress: 是否显示进度

        Returns:
            SceneDetectionResult: 检测结果
        """
        video_path = str(video_path)
        logger.info(f"Detecting scenes in: {video_path}")

        try:
            # 创建检测器
            if self.detector_type == "content" or self.detector_type == "threshold":
                detector = self._detector_class(threshold=threshold)
            else:  # adaptive
                detector = self._detector_class()

            # 执行检测
            scene_list = detect(
                video_path,
                detector,
                show_progress=show_progress,
            )

            # 过滤短场景并转换
            scenes = []
            for start_time, end_time in scene_list:
                duration = end_time.get_seconds() - start_time.get_seconds()
                if duration >= min_scene_len:
                    scenes.append(
                        Scene(
                            start=start_time.get_seconds(),
                            end=end_time.get_seconds(),
                            start_frame=start_time.get_frames(),
                            end_frame=end_time.get_frames(),
                        )
                    )

            # 计算总时长
            total_duration = scenes[-1].end if scenes else 0

            result = SceneDetectionResult(
                scenes=scenes,
                video_path=video_path,
                detector_type=self.detector_type,
                total_duration=total_duration,
            )

            logger.info(f"Scene detection complete: {len(scenes)} scenes found")
            return result

        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
            raise

    def split_video(
        self,
        video_path: Union[str, Path],
        scenes: List[Scene],
        output_dir: Union[str, Path],
        filename_template: str = "scene_{:03d}.mp4",
        show_progress: bool = False,
    ) -> List[Path]:
        """按场景分割视频.

        Args:
            video_path: 视频路径
            scenes: 场景列表
            output_dir: 输出目录
            filename_template: 文件名模板
            show_progress: 是否显示进度

        Returns:
            分割后的视频路径列表
        """
        video_path = str(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 转换场景列表为 PySceneDetect 格式
        scene_tuples = [(s.start, s.end) for s in scenes]

        try:
            # Use output_file_template instead of filename_template
            # $VIDEO_NAME-Scene-$SCENE_NUMBER.mp4
            output_file_template = filename_template.replace("{}", "$SCENE_NUMBER")
            if "$VIDEO_NAME" not in output_file_template:
                output_file_template = "scene-$SCENE_NUMBER.mp4"

            split_video_ffmpeg(
                video_path,
                scene_tuples,
                output_dir=output_dir,
                output_file_template=output_file_template,
                show_progress=show_progress,
            )

            # 收集输出文件
            video_name = Path(video_path).stem
            output_files = [
                output_dir / output_file_template.replace("$VIDEO_NAME", video_name).replace("$SCENE_NUMBER", str(i + 1))
                for i in range(len(scenes))
            ]

            logger.info(f"Video split into {len(output_files)} scenes")
            return output_files

        except Exception as e:
            logger.error(f"Video splitting failed: {e}")
            raise

    def detect_with_multiple_methods(
        self,
        video_path: Union[str, Path],
        methods: Optional[List[str]] = None,
    ) -> Dict[str, SceneDetectionResult]:
        """使用多种方法检测场景，返回综合结果.

        Args:
            video_path: 视频路径
            methods: 检测方法列表，None 则使用所有方法

        Returns:
            各方法的检测结果字典
        """
        methods = methods or list(self.DETECTOR_TYPES.keys())
        results = {}

        for method in methods:
            logger.info(f"Trying detection method: {method}")
            detector = SceneDetector(detector_type=method)
            try:
                result = detector.detect(video_path)
                results[method] = result
            except Exception as e:
                logger.warning(f"Method {method} failed: {e}")

        return results

    def merge_similar_scenes(
        self,
        scenes: List[Scene],
        max_merge_gap: float = 1.0,
        min_merged_duration: float = 2.0,
    ) -> List[Scene]:
        """合并相似/接近的场景.

        Args:
            scenes: 场景列表
            max_merge_gap: 最大合并间隔（秒）
            min_merged_duration: 合并后最小时长

        Returns:
            合并后的场景列表
        """
        if not scenes:
            return []

        merged = []
        current = scenes[0]

        for next_scene in scenes[1:]:
            gap = next_scene.start - current.end

            if gap <= max_merge_gap:
                # 合并场景
                current = Scene(
                    start=current.start,
                    end=next_scene.end,
                    start_frame=current.start_frame,
                    end_frame=next_scene.end_frame,
                )
            else:
                # 保存当前场景
                if current.duration >= min_merged_duration:
                    merged.append(current)
                current = next_scene

        # 添加最后一个场景
        if current.duration >= min_merged_duration:
            merged.append(current)

        logger.info(f"Merged scenes: {len(scenes)} -> {len(merged)}")
        return merged
