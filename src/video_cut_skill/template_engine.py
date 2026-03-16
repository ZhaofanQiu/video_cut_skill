"""Motion Graphics Template System.

提供可复用的动效模板系统，支持 JSON/YAML 定义和参数化渲染。
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from video_cut_skill.motion_graphics import (
    EasingFunction,
    EasingType,
    MGSpec,
    MotionGraphicsRenderer,
    ShapeElement,
    ShapeStyle,
    ShapeType,
    TextAlign,
    TextAnimation,
    TextAnimationConfig,
    TextElement,
    TextStyle,
)


class TemplateType(Enum):
    """模板类型枚举."""
    INTRO = "intro"              # 片头
    OUTRO = "outro"              # 片尾
    LOWER_THIRD = "lower_third"  # 字幕条
    TRANSITION = "transition"    # 转场
    QUOTE_CARD = "quote_card"    # 引用卡片
    TITLE_CARD = "title_card"    # 标题卡片
    DATA_VISUALIZATION = "data_visualization"  # 数据可视化
    CUSTOM = "custom"            # 自定义


class ParameterType(Enum):
    """参数类型枚举."""
    STRING = "string"
    NUMBER = "number"
    COLOR = "color"
    BOOLEAN = "boolean"
    SELECT = "select"
    FILE = "file"


@dataclass
class TemplateParameter:
    """模板参数定义.
    
    Attributes:
        name: 参数名称
        param_type: 参数类型
        required: 是否必需
        default: 默认值
        description: 参数描述
        options: 选项列表（用于 select 类型）
        validation: 验证规则
    """
    name: str
    param_type: ParameterType
    required: bool = True
    default: Any = None
    description: str = ""
    options: Optional[List[str]] = None
    validation: Optional[Dict[str, Any]] = None
    
    def validate_value(self, value: Any) -> bool:
        """验证参数值."""
        if value is None:
            return not self.required
        
        if self.param_type == ParameterType.STRING:
            return isinstance(value, str)
        
        elif self.param_type == ParameterType.NUMBER:
            if not isinstance(value, (int, float)):
                return False
            if self.validation:
                min_val = self.validation.get("min")
                max_val = self.validation.get("max")
                if min_val is not None and value < min_val:
                    return False
                if max_val is not None and value > max_val:
                    return False
            return True
        
        elif self.param_type == ParameterType.COLOR:
            if not isinstance(value, str):
                return False
            # 简单验证颜色格式
            return bool(re.match(r"^#[0-9A-Fa-f]{6}$", value))
        
        elif self.param_type == ParameterType.BOOLEAN:
            return isinstance(value, bool)
        
        elif self.param_type == ParameterType.SELECT:
            return value in (self.options or [])
        
        return True


@dataclass
class MotionTemplate:
    """动效模板定义.
    
    Attributes:
        template_id: 模板唯一ID
        name: 模板名称
        template_type: 模板类型
        version: 版本号
        description: 模板描述
        author: 作者
        parameters: 参数定义列表
        elements: 元素定义列表
        duration: 默认时长（秒）
        resolution: 默认分辨率
        tags: 标签列表
        preview_image: 预览图路径
    """
    template_id: str
    name: str
    template_type: TemplateType
    version: str = "1.0"
    description: str = ""
    author: str = ""
    parameters: List[TemplateParameter] = field(default_factory=list)
    elements: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 3.0
    resolution: tuple = (1920, 1080)
    tags: List[str] = field(default_factory=list)
    preview_image: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "template_type": self.template_type.value,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.param_type.value,
                    "required": p.required,
                    "default": p.default,
                    "description": p.description,
                    "options": p.options,
                    "validation": p.validation
                }
                for p in self.parameters
            ],
            "elements": self.elements,
            "duration": self.duration,
            "resolution": self.resolution,
            "tags": self.tags,
            "preview_image": self.preview_image
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MotionTemplate":
        """从字典创建."""
        params = []
        for p in data.get("parameters", []):
            params.append(TemplateParameter(
                name=p["name"],
                param_type=ParameterType(p["type"]),
                required=p.get("required", True),
                default=p.get("default"),
                description=p.get("description", ""),
                options=p.get("options"),
                validation=p.get("validation")
            ))
        
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            template_type=TemplateType(data["template_type"]),
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            parameters=params,
            elements=data.get("elements", []),
            duration=data.get("duration", 3.0),
            resolution=tuple(data.get("resolution", [1920, 1080])),
            tags=data.get("tags", []),
            preview_image=data.get("preview_image")
        )
    
    def validate_parameters(self, values: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证参数值.
        
        Args:
            values: 参数值字典
            
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        for param in self.parameters:
            value = values.get(param.name, param.default)
            
            if param.required and value is None:
                errors.append(f"Missing required parameter: {param.name}")
                continue
            
            if value is not None and not param.validate_value(value):
                errors.append(f"Invalid value for parameter {param.name}: {value}")
        
        return len(errors) == 0, errors
    
    def apply_parameters(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """应用参数到模板.
        
        Args:
            values: 参数值字典
            
        Returns:
            应用参数后的元素定义
        """
        # 合并默认值和提供的值
        merged = {}
        for param in self.parameters:
            merged[param.name] = values.get(param.name, param.default)
        
        # 替换元素中的参数占位符
        def replace_placeholders(obj: Any) -> Any:
            if isinstance(obj, str):
                result = obj
                for key, value in merged.items():
                    placeholder = f"{{{{{key}}}}}"
                    if placeholder in result:
                        result = result.replace(placeholder, str(value))
                return result
            elif isinstance(obj, dict):
                return {k: replace_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(item) for item in obj]
            return obj
        
        return replace_placeholders(self.elements)


class TemplateEngine:
    """模板引擎.
    
    管理模板的加载、渲染和存储。
    
    Example:
        >>> engine = TemplateEngine()
        >>>
        >>> # 加载模板
        >>> template = engine.load_template("youtube_intro")
        >>>
        >>> # 渲染模板
        >>> elements = engine.render_template(
        ...     "youtube_intro",
        ...     {"channel_name": "My Channel", "accent_color": "#FF0000"}
        ... )
        >>>
        >>> # 创建自定义模板
        >>> template = MotionTemplate(
        ...     template_id="my_intro",
        ...     name="My Intro",
        ...     template_type=TemplateType.INTRO,
        ...     parameters=[
        ...         TemplateParameter("title", ParameterType.STRING, required=True)
        ...     ],
        ...     elements=[...]
        ... )
        >>> engine.register_template(template)
    """
    
    def __init__(self, template_dir: Optional[Union[str, Path]] = None):
        """初始化模板引擎.
        
        Args:
            template_dir: 模板存储目录
        """
        self.template_dir = Path(template_dir) if template_dir else None
        self._templates: Dict[str, MotionTemplate] = {}
        self._renderer = MotionGraphicsRenderer()
        
        # 加载内置模板
        self._load_builtin_templates()
        
        # 加载用户模板
        if self.template_dir:
            self._load_user_templates()
    
    def register_template(self, template: MotionTemplate) -> None:
        """注册模板.
        
        Args:
            template: 模板对象
        """
        self._templates[template.template_id] = template
    
    def unregister_template(self, template_id: str) -> bool:
        """注销模板.
        
        Args:
            template_id: 模板ID
            
        Returns:
            是否成功
        """
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False
    
    def get_template(self, template_id: str) -> Optional[MotionTemplate]:
        """获取模板.
        
        Args:
            template_id: 模板ID
            
        Returns:
            模板对象，如果不存在返回None
        """
        return self._templates.get(template_id)
    
    def list_templates(
        self,
        template_type: Optional[TemplateType] = None,
        tags: Optional[List[str]] = None
    ) -> List[MotionTemplate]:
        """列出模板.
        
        Args:
            template_type: 按类型过滤
            tags: 按标签过滤
            
        Returns:
            模板列表
        """
        templates = list(self._templates.values())
        
        if template_type:
            templates = [t for t in templates if t.template_type == template_type]
        
        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]
        
        return templates
    
    def render_template(
        self,
        template_id: str,
        parameters: Dict[str, Any]
    ) -> List[Union[TextElement, ShapeElement]]:
        """渲染模板.
        
        Args:
            template_id: 模板ID
            parameters: 参数值
            
        Returns:
            渲染后的元素列表
            
        Raises:
            ValueError: 如果模板不存在或参数无效
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # 验证参数
        valid, errors = template.validate_parameters(parameters)
        if not valid:
            raise ValueError(f"Invalid parameters: {', '.join(errors)}")
        
        # 应用参数
        elements_data = template.apply_parameters(parameters)
        
        # 转换为元素对象
        elements = []
        for elem_data in elements_data:
            elem = self._create_element_from_dict(elem_data)
            if elem:
                elements.append(elem)
        
        return elements
    
    def render_to_video(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        output_path: Union[str, Path],
        fps: float = 30.0
    ) -> str:
        """渲染模板到视频.
        
        Args:
            template_id: 模板ID
            parameters: 参数值
            output_path: 输出路径
            fps: 帧率
            
        Returns:
            输出文件路径
        """
        elements = self.render_template(template_id, parameters)
        template = self._templates.get(template_id)
        
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # 创建 Motion Graphics Spec
        spec = MGSpec(
            width=template.resolution[0],
            height=template.resolution[1],
            duration=template.duration,
            fps=fps,
            elements=elements
        )
        
        # 渲染
        self._renderer.render(spec, output_path)
        
        return str(output_path)
    
    def save_template(
        self,
        template: MotionTemplate,
        format: str = "yaml"
    ) -> str:
        """保存模板到文件.
        
        Args:
            template: 模板对象
            format: 格式 ("yaml" 或 "json")
            
        Returns:
            保存的文件路径
        """
        if not self.template_dir:
            raise ValueError("Template directory not configured")
        
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{template.template_id}.{format}"
        filepath = self.template_dir / filename
        
        data = template.to_dict()
        
        with open(filepath, "w", encoding="utf-8") as f:
            if format == "yaml":
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def load_template_from_file(
        self,
        filepath: Union[str, Path]
    ) -> MotionTemplate:
        """从文件加载模板.
        
        Args:
            filepath: 文件路径
            
        Returns:
            模板对象
        """
        filepath = Path(filepath)
        
        with open(filepath, "r", encoding="utf-8") as f:
            if filepath.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        template = MotionTemplate.from_dict(data)
        self.register_template(template)
        
        return template
    
    def _load_builtin_templates(self) -> None:
        """加载内置模板."""
        # YouTube 片头模板
        self._register_youtube_intro()
        
        # Lower Thirds 模板
        self._register_lower_third()
        
        # Quote Card 模板
        self._register_quote_card()
        
        # Title Card 模板
        self._register_title_card()
    
    def _load_user_templates(self) -> None:
        """加载用户模板目录."""
        if not self.template_dir or not self.template_dir.exists():
            return
        
        for ext in ("*.yaml", "*.yml", "*.json"):
            for filepath in self.template_dir.glob(ext):
                try:
                    self.load_template_from_file(filepath)
                except Exception as e:
                    print(f"Failed to load template {filepath}: {e}")
    
    def _create_element_from_dict(
        self,
        data: Dict[str, Any]
    ) -> Optional[Union[TextElement, ShapeElement]]:
        """从字典创建元素."""
        elem_type = data.get("type")
        
        if elem_type == "text":
            return self._create_text_element(data)
        elif elem_type == "shape":
            return self._create_shape_element(data)
        
        return None
    
    def _create_text_element(self, data: Dict[str, Any]) -> TextElement:
        """创建文本元素."""
        style = TextStyle(
            font_size=data.get("style", {}).get("font_size", 64),
            font_color=data.get("style", {}).get("font_color", "#FFFFFF"),
            font_family=data.get("style", {}).get("font_family", "Arial"),
            font_weight=data.get("style", {}).get("font_weight", "normal"),
        )
        
        # 解析动画配置
        entry_anim = None
        if "entry_animation" in data:
            anim_data = data["entry_animation"]
            entry_anim = TextAnimationConfig(
                animation_type=TextAnimation(anim_data.get("type", "fade_in")),
                duration=anim_data.get("duration", 0.5),
                easing=anim_data.get("easing", "ease_out")
            )
        
        return TextElement(
            text=data.get("text", ""),
            position=tuple(data.get("position", [960, 540])),
            style=style,
            start_time=data.get("start_time", 0),
            end_time=data.get("end_time", 3),
            entry_animation=entry_anim
        )
    
    def _create_shape_element(self, data: Dict[str, Any]) -> ShapeElement:
        """创建形状元素."""
        style = ShapeStyle(
            fill_color=data.get("style", {}).get("fill_color", "#FFFFFF"),
            stroke_color=data.get("style", {}).get("stroke_color"),
            stroke_width=data.get("style", {}).get("stroke_width", 0),
            opacity=data.get("style", {}).get("opacity", 1.0),
        )
        
        return ShapeElement(
            shape_type=ShapeType(data.get("shape", "rectangle")),
            position=tuple(data.get("position", [960, 540])),
            size=tuple(data.get("size", [100, 100])),
            style=style,
            start_time=data.get("start_time", 0),
            end_time=data.get("end_time", 3),
        )
    
    def _register_youtube_intro(self) -> None:
        """注册 YouTube 片头模板."""
        template = MotionTemplate(
            template_id="youtube_intro_v1",
            name="YouTube Intro",
            template_type=TemplateType.INTRO,
            description="经典 YouTube 频道片头动画",
            version="1.0",
            duration=3.0,
            parameters=[
                TemplateParameter(
                    name="channel_name",
                    param_type=ParameterType.STRING,
                    required=True,
                    description="频道名称"
                ),
                TemplateParameter(
                    name="accent_color",
                    param_type=ParameterType.COLOR,
                    required=False,
                    default="#FF0000",
                    description="强调色"
                ),
                TemplateParameter(
                    name="subtitle",
                    param_type=ParameterType.STRING,
                    required=False,
                    default="",
                    description="副标题"
                ),
            ],
            elements=[
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "position": [960, 540],
                    "size": [1920, 1080],
                    "style": {"fill_color": "{{accent_color}}", "opacity": 0.1},
                    "start_time": 0,
                    "end_time": 3
                },
                {
                    "type": "text",
                    "text": "{{channel_name}}",
                    "position": [960, 500],
                    "style": {
                        "font_size": 96,
                        "font_color": "#FFFFFF",
                        "font_weight": "bold"
                    },
                    "entry_animation": {
                        "type": "slide_up",
                        "duration": 0.5,
                        "easing": "ease_out_back"
                    },
                    "start_time": 0.3,
                    "end_time": 2.7
                },
                {
                    "type": "text",
                    "text": "{{subtitle}}",
                    "position": [960, 600],
                    "style": {
                        "font_size": 36,
                        "font_color": "#CCCCCC"
                    },
                    "entry_animation": {
                        "type": "fade_in",
                        "duration": 0.5
                    },
                    "start_time": 0.8,
                    "end_time": 2.5
                },
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "position": [960, 650],
                    "size": [200, 4],
                    "style": {"fill_color": "{{accent_color}}"},
                    "entry_animation": {
                        "type": "scale_x",
                        "duration": 0.3
                    },
                    "start_time": 1.0,
                    "end_time": 2.5
                }
            ],
            tags=["youtube", "intro", "channel"]
        )
        
        self.register_template(template)
    
    def _register_lower_third(self) -> None:
        """注册 Lower Thirds 模板."""
        template = MotionTemplate(
            template_id="lower_third_v1",
            name="Lower Third",
            template_type=TemplateType.LOWER_THIRD,
            description="新闻风格的字幕条",
            version="1.0",
            duration=5.0,
            parameters=[
                TemplateParameter(
                    name="name",
                    param_type=ParameterType.STRING,
                    required=True,
                    description="人名"
                ),
                TemplateParameter(
                    name="title",
                    param_type=ParameterType.STRING,
                    required=False,
                    default="",
                    description="职位/头衔"
                ),
                TemplateParameter(
                    name="color",
                    param_type=ParameterType.COLOR,
                    required=False,
                    default="#0066CC",
                    description="颜色"
                ),
            ],
            elements=[
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "position": [400, 900],
                    "size": [600, 80],
                    "style": {"fill_color": "{{color}}", "opacity": 0.9},
                    "entry_animation": {"type": "slide_left", "duration": 0.4},
                    "start_time": 0,
                    "end_time": 5
                },
                {
                    "type": "text",
                    "text": "{{name}}",
                    "position": [400, 885],
                    "style": {
                        "font_size": 40,
                        "font_color": "#FFFFFF",
                        "font_weight": "bold"
                    },
                    "entry_animation": {"type": "fade_in", "duration": 0.3},
                    "start_time": 0.2,
                    "end_time": 4.8
                },
                {
                    "type": "text",
                    "text": "{{title}}",
                    "position": [400, 925],
                    "style": {
                        "font_size": 24,
                        "font_color": "#CCCCCC"
                    },
                    "entry_animation": {"type": "fade_in", "duration": 0.3},
                    "start_time": 0.3,
                    "end_time": 4.7
                }
            ],
            tags=["news", "lower_third", "subtitle"]
        )
        
        self.register_template(template)
    
    def _register_quote_card(self) -> None:
        """注册 Quote Card 模板."""
        template = MotionTemplate(
            template_id="quote_card_v1",
            name="Quote Card",
            template_type=TemplateType.QUOTE_CARD,
            description="引用卡片，适合展示名言金句",
            version="1.0",
            duration=4.0,
            parameters=[
                TemplateParameter(
                    name="quote",
                    param_type=ParameterType.STRING,
                    required=True,
                    description="引用内容"
                ),
                TemplateParameter(
                    name="author",
                    param_type=ParameterType.STRING,
                    required=False,
                    default="",
                    description="作者"
                ),
                TemplateParameter(
                    name="background_color",
                    param_type=ParameterType.COLOR,
                    required=False,
                    default="#1A1A1A",
                    description="背景色"
                ),
            ],
            elements=[
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "position": [960, 540],
                    "size": [1600, 600],
                    "style": {"fill_color": "{{background_color}}"},
                    "start_time": 0,
                    "end_time": 4
                },
                {
                    "type": "text",
                    "text": "\"{{quote}}\"",
                    "position": [960, 500],
                    "style": {
                        "font_size": 48,
                        "font_color": "#FFFFFF",
                        "font_style": "italic"
                    },
                    "entry_animation": {"type": "fade_in", "duration": 0.6},
                    "start_time": 0.3,
                    "end_time": 3.5
                },
                {
                    "type": "text",
                    "text": "— {{author}}",
                    "position": [1200, 700],
                    "style": {
                        "font_size": 32,
                        "font_color": "#999999"
                    },
                    "entry_animation": {"type": "fade_in", "duration": 0.4},
                    "start_time": 0.8,
                    "end_time": 3.5
                }
            ],
            tags=["quote", "card", "text"]
        )
        
        self.register_template(template)
    
    def _register_title_card(self) -> None:
        """注册 Title Card 模板."""
        template = MotionTemplate(
            template_id="title_card_v1",
            name="Title Card",
            template_type=TemplateType.TITLE_CARD,
            description="章节标题卡片",
            version="1.0",
            duration=2.5,
            parameters=[
                TemplateParameter(
                    name="title",
                    param_type=ParameterType.STRING,
                    required=True,
                    description="标题"
                ),
                TemplateParameter(
                    name="chapter_number",
                    param_type=ParameterType.NUMBER,
                    required=False,
                    default=1,
                    description="章节编号"
                ),
                TemplateParameter(
                    name="color",
                    param_type=ParameterType.COLOR,
                    required=False,
                    default="#FFD700",
                    description="强调色"
                ),
            ],
            elements=[
                {
                    "type": "text",
                    "text": "CHAPTER {{chapter_number}}",
                    "position": [960, 480],
                    "style": {
                        "font_size": 28,
                        "font_color": "{{color}}",
                        "letter_spacing": 4
                    },
                    "entry_animation": {"type": "fade_in", "duration": 0.4},
                    "start_time": 0.2,
                    "end_time": 2.3
                },
                {
                    "type": "text",
                    "text": "{{title}}",
                    "position": [960, 540],
                    "style": {
                        "font_size": 72,
                        "font_color": "#FFFFFF",
                        "font_weight": "bold"
                    },
                    "entry_animation": {"type": "slide_up", "duration": 0.5},
                    "start_time": 0.4,
                    "end_time": 2.3
                },
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "position": [960, 600],
                    "size": [100, 4],
                    "style": {"fill_color": "{{color}}"},
                    "entry_animation": {"type": "scale_x", "duration": 0.3},
                    "start_time": 0.8,
                    "end_time": 2.3
                }
            ],
            tags=["title", "chapter", "section"]
        )
        
        self.register_template(template)


# 便捷函数

def render_template_quick(
    template_id: str,
    parameters: Dict[str, Any],
    template_dir: Optional[Union[str, Path]] = None
) -> List[Union[TextElement, ShapeElement]]:
    """快速渲染模板.
    
    Args:
        template_id: 模板ID
        parameters: 参数值
        template_dir: 模板目录
        
    Returns:
        渲染后的元素列表
    """
    engine = TemplateEngine(template_dir)
    return engine.render_template(template_id, parameters)


def create_youtube_intro(
    channel_name: str,
    subtitle: str = "",
    accent_color: str = "#FF0000"
) -> List[Union[TextElement, ShapeElement]]:
    """快速创建 YouTube 片头.
    
    Args:
        channel_name: 频道名称
        subtitle: 副标题
        accent_color: 强调色
        
    Returns:
        元素列表
    """
    return render_template_quick(
        "youtube_intro_v1",
        {
            "channel_name": channel_name,
            "subtitle": subtitle,
            "accent_color": accent_color
        }
    )


def create_lower_third(
    name: str,
    title: str = "",
    color: str = "#0066CC"
) -> List[Union[TextElement, ShapeElement]]:
    """快速创建 Lower Thirds 字幕条.
    
    Args:
        name: 人名
        title: 职位/头衔
        color: 颜色
        
    Returns:
        元素列表
    """
    return render_template_quick(
        "lower_third_v1",
        {
            "name": name,
            "title": title,
            "color": color
        }
    )
