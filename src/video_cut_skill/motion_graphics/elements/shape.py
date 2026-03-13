"""Shape Element - 形状元素."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Union, List


class ShapeType(Enum):
    """形状类型."""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    LINE = "line"
    POLYGON = "polygon"


@dataclass
class ShapeStyle:
    """形状样式."""
    
    # 填充
    fill_color: Optional[str] = "#FFFFFF"
    fill_opacity: float = 1.0
    
    # 描边
    stroke_color: Optional[str] = None
    stroke_width: int = 0
    stroke_opacity: float = 1.0
    
    # 圆角 (用于矩形)
    corner_radius: int = 0


@dataclass
class ShapeElement:
    """形状元素.
    
    用于创建各种形状叠加效果.
    
    Example:
        >>> # 创建一个半透明黑色遮罩
        >>> mask = ShapeElement.rectangle(
        ...     x=0, y=0, width=1920, height=1080,
        ...     style=ShapeStyle(fill_color="#000000", fill_opacity=0.5)
        ... )
        
        >>> # 创建一个圆形头像框
        >>> circle = ShapeElement.circle(
        ...     cx=960, cy=540, radius=100,
        ...     style=ShapeStyle(
        ...         fill_color="#FFFFFF",
        ...         stroke_color="#FF0000",
        ...         stroke_width=5
        ...     )
        ... )
    """
    
    shape_type: ShapeType
    
    # 位置和尺寸参数 (根据形状类型不同)
    params: dict
    
    # 样式
    style: ShapeStyle = None
    
    # 显示时间
    start_time: float = 0.0
    end_time: float = 5.0
    
    def __post_init__(self):
        """初始化默认值."""
        if self.style is None:
            self.style = ShapeStyle()
    
    @classmethod
    def rectangle(
        cls,
        x: int,
        y: int,
        width: int,
        height: int,
        style: Optional[ShapeStyle] = None,
        start_time: float = 0.0,
        end_time: float = 5.0,
    ) -> "ShapeElement":
        """创建矩形."""
        return cls(
            shape_type=ShapeType.RECTANGLE,
            params={"x": x, "y": y, "width": width, "height": height},
            style=style or ShapeStyle(),
            start_time=start_time,
            end_time=end_time,
        )
    
    @classmethod
    def circle(
        cls,
        cx: int,
        cy: int,
        radius: int,
        style: Optional[ShapeStyle] = None,
        start_time: float = 0.0,
        end_time: float = 5.0,
    ) -> "ShapeElement":
        """创建圆形."""
        return cls(
            shape_type=ShapeType.CIRCLE,
            params={"cx": cx, "cy": cy, "radius": radius},
            style=style or ShapeStyle(),
            start_time=start_time,
            end_time=end_time,
        )
    
    @classmethod
    def ellipse(
        cls,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        style: Optional[ShapeStyle] = None,
        start_time: float = 0.0,
        end_time: float = 5.0,
    ) -> "ShapeElement":
        """创建椭圆."""
        return cls(
            shape_type=ShapeType.ELLIPSE,
            params={"cx": cx, "cy": cy, "rx": rx, "ry": ry},
            style=style or ShapeStyle(),
            start_time=start_time,
            end_time=end_time,
        )
    
    @classmethod
    def line(
        cls,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        stroke_width: int = 2,
        stroke_color: str = "#FFFFFF",
        start_time: float = 0.0,
        end_time: float = 5.0,
    ) -> "ShapeElement":
        """创建线条."""
        return cls(
            shape_type=ShapeType.LINE,
            params={"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            style=ShapeStyle(
                fill_color=None,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
            ),
            start_time=start_time,
            end_time=end_time,
        )
    
    @property
    def duration(self) -> float:
        """显示时长."""
        return self.end_time - self.start_time
    
    def is_visible_at(self, time: float) -> bool:
        """检查在指定时间是否可见."""
        return self.start_time <= time < self.end_time
    
    def to_svg(self) -> str:
        """转换为 SVG 字符串.
        
        Returns:
            SVG 元素字符串
        """
        style = self.style
        
        # 构建样式字符串
        styles = []
        if style.fill_color and style.fill_opacity > 0:
            styles.append(f"fill:{style.fill_color}")
            styles.append(f"fill-opacity:{style.fill_opacity}")
        else:
            styles.append("fill:none")
        
        if style.stroke_color and style.stroke_width > 0:
            styles.append(f"stroke:{style.stroke_color}")
            styles.append(f"stroke-width:{style.stroke_width}")
            styles.append(f"stroke-opacity:{style.stroke_opacity}")
        
        style_str = ";".join(styles)
        
        if self.shape_type == ShapeType.RECTANGLE:
            x = self.params["x"]
            y = self.params["y"]
            width = self.params["width"]
            height = self.params["height"]
            rx = style.corner_radius
            return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{rx}" style="{style_str}" />'
        
        elif self.shape_type == ShapeType.CIRCLE:
            cx = self.params["cx"]
            cy = self.params["cy"]
            r = self.params["radius"]
            return f'<circle cx="{cx}" cy="{cy}" r="{r}" style="{style_str}" />'
        
        elif self.shape_type == ShapeType.ELLIPSE:
            cx = self.params["cx"]
            cy = self.params["cy"]
            rx = self.params["rx"]
            ry = self.params["ry"]
            return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" style="{style_str}" />'
        
        elif self.shape_type == ShapeType.LINE:
            x1 = self.params["x1"]
            y1 = self.params["y1"]
            x2 = self.params["x2"]
            y2 = self.params["y2"]
            return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="{style_str}" />'
        
        return ""
    
    def __repr__(self) -> str:
        return f"ShapeElement({self.shape_type.value})"
