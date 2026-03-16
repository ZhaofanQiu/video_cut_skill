"""Metrics collection and monitoring for video processing.

提供性能指标收集、监控和告警功能。
"""

import json
import time
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
from collections import deque
import logging

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型枚举."""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 瞬时值
    HISTOGRAM = "histogram"  # 分布值
    TIMER = "timer"          # 计时器


class AlertSeverity(Enum):
    """告警级别枚举."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """单个指标值.
    
    Attributes:
        name: 指标名称
        value: 指标值
        metric_type: 指标类型
        timestamp: 时间戳
        labels: 标签 (如 task_id, stage 等)
    """
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp,
            "labels": self.labels
        }


@dataclass
class TaskMetrics:
    """单个任务的性能指标.
    
    Attributes:
        task_id: 任务ID
        task_type: 任务类型
        input_size_mb: 输入文件大小(MB)
        output_size_mb: 输出文件大小(MB)
        wait_time_seconds: 等待时间(秒)
        process_time_seconds: 处理时间(秒)
        stages: 各阶段耗时
    """
    task_id: str
    task_type: str
    
    # 文件信息
    input_size_mb: float = 0.0
    output_size_mb: float = 0.0
    
    # 时间指标
    submitted_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # 各阶段耗时
    stages: Dict[str, float] = field(default_factory=dict)
    
    # 资源使用
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    peak_gpu_memory_mb: float = 0.0
    
    # 成本
    estimated_cost_yuan: float = 0.0
    
    # 结果
    success: bool = False
    error_message: Optional[str] = None
    
    @property
    def wait_time_seconds(self) -> float:
        """等待时间."""
        if self.started_at is None:
            return time.time() - self.submitted_at
        return self.started_at - self.submitted_at
    
    @property
    def process_time_seconds(self) -> Optional[float]:
        """处理时间."""
        if self.started_at is None:
            return None
        end = self.completed_at or time.time()
        return end - self.started_at
    
    @property
    def total_time_seconds(self) -> float:
        """总时间."""
        end = self.completed_at or time.time()
        return end - self.submitted_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "input_size_mb": self.input_size_mb,
            "output_size_mb": self.output_size_mb,
            "wait_time_seconds": self.wait_time_seconds,
            "process_time_seconds": self.process_time_seconds,
            "total_time_seconds": self.total_time_seconds,
            "stages": self.stages,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
            "peak_gpu_memory_mb": self.peak_gpu_memory_mb,
            "estimated_cost_yuan": self.estimated_cost_yuan,
            "success": self.success,
            "error_message": self.error_message
        }


@dataclass
class SystemMetrics:
    """系统级指标.
    
    Attributes:
        timestamp: 时间戳
        cpu_percent: CPU使用率
        memory_percent: 内存使用率
        disk_percent: 磁盘使用率
        gpu_metrics: GPU指标 (如果有)
    """
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_free_gb: float
    gpu_metrics: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Alert:
    """告警信息.
    
    Attributes:
        alert_id: 告警ID
        severity: 严重级别
        title: 标题
        message: 详细消息
        metric_name: 触发的指标名
        threshold: 阈值
        current_value: 当前值
        timestamp: 时间戳
    """
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "current_value": self.current_value,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged
        }


class MetricsCollector:
    """性能指标收集器.
    
    收集视频处理任务的性能指标，提供统计分析和告警功能。
    
    Example:
        >>> collector = MetricsCollector()
        >>> 
        >>> # 记录任务开始
        >>> task_metrics = collector.start_task("task_001", "edit")
        >>> 
        >>> # 记录阶段耗时
        >>> with collector.time_stage("task_001", "transcription"):
        ...     result = transcribe(audio_path)
        >>> 
        >>> # 记录任务完成
        >>> collector.complete_task("task_001", success=True)
        >>> 
        >>> # 获取统计
        >>> stats = collector.get_statistics(time_range="24h")
    """
    
    def __init__(
        self,
        metrics_dir: str = "~/.video_cut_skill/metrics",
        max_history: int = 10000,
        system_metrics_interval: float = 60.0,
        enable_system_monitoring: bool = True
    ):
        """初始化指标收集器.
        
        Args:
            metrics_dir: 指标存储目录
            max_history: 最大历史记录数
            system_metrics_interval: 系统指标采集间隔(秒)
            enable_system_monitoring: 是否启用系统监控
        """
        self.metrics_dir = Path(metrics_dir).expanduser()
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.max_history = max_history
        self.system_metrics_interval = system_metrics_interval
        
        # 任务指标存储
        self._task_metrics: Dict[str, TaskMetrics] = {}
        self._completed_tasks: deque = deque(maxlen=max_history)
        
        # 指标值存储
        self._metrics: Dict[str, List[MetricValue]] = {}
        
        # 告警
        self._alerts: List[Alert] = []
        self._alert_handlers: List[Callable[[Alert], None]] = []
        self._alert_rules: List[Dict[str, Any]] = []
        
        # 系统监控
        self._enable_system_monitoring = enable_system_monitoring
        self._system_metrics: deque = deque(maxlen=1000)
        self._system_monitor_task = None
    
    async def initialize(self) -> None:
        """初始化，启动系统监控."""
        if self._enable_system_monitoring:
            self._system_monitor_task = asyncio.create_task(self._system_monitor_loop())
        
        # 加载历史数据
        self._load_history()
        
        logger.info("MetricsCollector initialized")
    
    async def shutdown(self) -> None:
        """关闭，保存数据."""
        if self._system_monitor_task:
            self._system_monitor_task.cancel()
            try:
                await self._system_monitor_task
            except asyncio.CancelledError:
                pass
        
        self._save_history()
        logger.info("MetricsCollector shutdown complete")
    
    def start_task(self, task_id: str, task_type: str) -> TaskMetrics:
        """开始记录任务指标.
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            
        Returns:
            任务指标对象
        """
        metrics = TaskMetrics(
            task_id=task_id,
            task_type=task_type,
            submitted_at=time.time()
        )
        self._task_metrics[task_id] = metrics
        
        logger.debug(f"Task metrics started: {task_id}, type={task_type}")
        return metrics
    
    def task_started(self, task_id: str) -> None:
        """标记任务开始处理."""
        if task_id in self._task_metrics:
            self._task_metrics[task_id].started_at = time.time()
    
    def record_stage(
        self,
        task_id: str,
        stage_name: str,
        duration_seconds: float
    ) -> None:
        """记录阶段耗时.
        
        Args:
            task_id: 任务ID
            stage_name: 阶段名称
            duration_seconds: 耗时(秒)
        """
        if task_id in self._task_metrics:
            self._task_metrics[task_id].stages[stage_name] = duration_seconds
            
            # 同时记录为指标
            self.record_metric(
                name=f"stage_duration_{stage_name}",
                value=duration_seconds,
                metric_type=MetricType.TIMER,
                labels={"task_id": task_id}
            )
    
    def time_stage(self, task_id: str, stage_name: str):
        """上下文管理器，自动计时阶段耗时.
        
        Example:
            with collector.time_stage("task_001", "transcription"):
                result = transcribe(audio_path)
        """
        return _StageTimer(self, task_id, stage_name)
    
    def complete_task(
        self,
        task_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        output_size_mb: float = 0.0
    ) -> None:
        """完成任务记录.
        
        Args:
            task_id: 任务ID
            success: 是否成功
            error_message: 错误消息
            output_size_mb: 输出文件大小
        """
        if task_id not in self._task_metrics:
            logger.warning(f"Task metrics not found: {task_id}")
            return
        
        metrics = self._task_metrics[task_id]
        metrics.completed_at = time.time()
        metrics.success = success
        metrics.error_message = error_message
        metrics.output_size_mb = output_size_mb
        
        # 移到已完成队列
        self._completed_tasks.append(metrics)
        del self._task_metrics[task_id]
        
        # 记录指标
        self.record_metric(
            name="task_duration",
            value=metrics.process_time_seconds or 0,
            metric_type=MetricType.TIMER,
            labels={"task_type": metrics.task_type, "success": str(success)}
        )
        
        logger.info(
            f"Task completed: {task_id}, success={success}, "
            f"duration={metrics.process_time_seconds:.1f}s"
        )
        
        # 检查告警规则
        self._check_alerts(metrics)
    
    def record_metric(
        self,
        name: str,
        value: Union[int, float],
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """记录指标值.
        
        Args:
            name: 指标名称
            value: 指标值
            metric_type: 指标类型
            labels: 标签
        """
        if name not in self._metrics:
            self._metrics[name] = []
        
        metric = MetricValue(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {}
        )
        
        self._metrics[name].append(metric)
        
        # 限制历史长度
        if len(self._metrics[name]) > self.max_history:
            self._metrics[name] = self._metrics[name][-self.max_history:]
    
    def record_resource_usage(
        self,
        task_id: str,
        memory_mb: float,
        cpu_percent: float,
        gpu_memory_mb: float = 0.0
    ) -> None:
        """记录资源使用情况.
        
        Args:
            task_id: 任务ID
            memory_mb: 内存使用(MB)
            cpu_percent: CPU使用率
            gpu_memory_mb: GPU显存使用(MB)
        """
        if task_id in self._task_metrics:
            metrics = self._task_metrics[task_id]
            metrics.peak_memory_mb = max(metrics.peak_memory_mb, memory_mb)
            metrics.peak_cpu_percent = max(metrics.peak_cpu_percent, cpu_percent)
            metrics.peak_gpu_memory_mb = max(metrics.peak_gpu_memory_mb, gpu_memory_mb)
    
    def record_cost(self, task_id: str, cost_yuan: float) -> None:
        """记录成本.
        
        Args:
            task_id: 任务ID
            cost_yuan: 成本(元)
        """
        if task_id in self._task_metrics:
            self._task_metrics[task_id].estimated_cost_yuan = cost_yuan
    
    def get_task_metrics(self, task_id: str) -> Optional[TaskMetrics]:
        """获取任务指标."""
        return self._task_metrics.get(task_id) or self._find_in_completed(task_id)
    
    def get_statistics(
        self,
        time_range: str = "24h",
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取统计信息.
        
        Args:
            time_range: 时间范围 (1h, 24h, 7d, 30d)
            task_type: 按任务类型过滤
            
        Returns:
            统计信息字典
        """
        # 解析时间范围
        seconds = self._parse_time_range(time_range)
        cutoff = time.time() - seconds
        
        # 筛选任务
        tasks = [
            t for t in self._completed_tasks
            if t.completed_at and t.completed_at >= cutoff
            and (task_type is None or t.task_type == task_type)
        ]
        
        if not tasks:
            return {
                "time_range": time_range,
                "total_tasks": 0,
                "success_rate": 0.0,
                "avg_process_time": 0.0,
                "p95_process_time": 0.0,
                "p99_process_time": 0.0
            }
        
        # 计算统计值
        process_times = [t.process_time_seconds for t in tasks if t.process_time_seconds]
        success_count = sum(1 for t in tasks if t.success)
        
        stats = {
            "time_range": time_range,
            "total_tasks": len(tasks),
            "success_count": success_count,
            "failed_count": len(tasks) - success_count,
            "success_rate": success_count / len(tasks),
            "avg_process_time": statistics.mean(process_times) if process_times else 0.0,
            "min_process_time": min(process_times) if process_times else 0.0,
            "max_process_time": max(process_times) if process_times else 0.0,
            "p50_process_time": statistics.median(process_times) if process_times else 0.0,
            "p95_process_time": self._percentile(process_times, 95) if process_times else 0.0,
            "p99_process_time": self._percentile(process_times, 99) if process_times else 0.0,
            "avg_wait_time": statistics.mean([t.wait_time_seconds for t in tasks]),
            "avg_input_size_mb": statistics.mean([t.input_size_mb for t in tasks if t.input_size_mb > 0]) or 0.0,
            "total_cost_yuan": sum(t.estimated_cost_yuan for t in tasks)
        }
        
        return stats
    
    def add_alert_rule(
        self,
        metric_name: str,
        threshold: float,
        comparison: str = "greater_than",
        severity: AlertSeverity = AlertSeverity.WARNING,
        title: Optional[str] = None,
        message_template: Optional[str] = None
    ) -> None:
        """添加告警规则.
        
        Args:
            metric_name: 指标名称
            threshold: 阈值
            comparison: 比较方式 (greater_than, less_than, equal)
            severity: 严重级别
            title: 告警标题
            message_template: 消息模板
        """
        rule = {
            "metric_name": metric_name,
            "threshold": threshold,
            "comparison": comparison,
            "severity": severity,
            "title": title or f"{metric_name} alert",
            "message_template": message_template or f"{metric_name} is {{value}}"
        }
        self._alert_rules.append(rule)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """添加告警处理器."""
        self._alert_handlers.append(handler)
    
    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        unacknowledged_only: bool = False
    ) -> List[Alert]:
        """获取告警列表."""
        alerts = self._alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def get_system_metrics(self, limit: int = 100) -> List[SystemMetrics]:
        """获取系统指标."""
        return list(self._system_metrics)[-limit:]
    
    def export_metrics(self, format: str = "json") -> str:
        """导出指标.
        
        Args:
            format: 导出格式 (json, prometheus)
            
        Returns:
            指标数据字符串
        """
        if format == "json":
            data = {
                "statistics": self.get_statistics("24h"),
                "active_tasks": len(self._task_metrics),
                "completed_tasks": len(self._completed_tasks),
                "alerts": len([a for a in self._alerts if not a.acknowledged])
            }
            return json.dumps(data, indent=2)
        
        elif format == "prometheus":
            lines = []
            stats = self.get_statistics("24h")
            
            lines.append(f'# HELP video_cut_tasks_total Total number of tasks')
            lines.append(f'# TYPE video_cut_tasks_total counter')
            lines.append(f'video_cut_tasks_total {stats["total_tasks"]}')
            
            lines.append(f'# HELP video_cut_success_rate Task success rate')
            lines.append(f'# TYPE video_cut_success_rate gauge')
            lines.append(f'video_cut_success_rate {stats["success_rate"]}')
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def _system_monitor_loop(self) -> None:
        """系统监控循环."""
        import psutil
        
        while True:
            try:
                # 收集系统指标
                metrics = SystemMetrics(
                    timestamp=time.time(),
                    cpu_percent=psutil.cpu_percent(interval=1),
                    memory_percent=psutil.virtual_memory().percent,
                    memory_used_mb=psutil.virtual_memory().used / (1024 * 1024),
                    memory_total_mb=psutil.virtual_memory().total / (1024 * 1024),
                    disk_percent=psutil.disk_usage('/').percent,
                    disk_free_gb=psutil.disk_usage('/').free / (1024 * 1024 * 1024)
                )
                
                # 尝试获取GPU信息
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    for i in range(pynvml.nvmlDeviceGetCount()):
                        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                        metrics.gpu_metrics.append({
                            "index": i,
                            "memory_used_mb": mem_info.used / (1024 * 1024),
                            "memory_total_mb": mem_info.total / (1024 * 1024),
                            "utilization_percent": util.gpu
                        })
                except Exception:
                    pass  # GPU监控可选
                
                self._system_metrics.append(metrics)
                
                # 检查资源告警
                if metrics.memory_percent > 90:
                    self._trigger_alert(
                        "memory_usage",
                        90.0,
                        metrics.memory_percent,
                        AlertSeverity.ERROR,
                        "High Memory Usage",
                        f"Memory usage is {metrics.memory_percent:.1f}%"
                    )
                
                if metrics.disk_percent > 90:
                    self._trigger_alert(
                        "disk_usage",
                        90.0,
                        metrics.disk_percent,
                        AlertSeverity.WARNING,
                        "Low Disk Space",
                        f"Disk usage is {metrics.disk_percent:.1f}%"
                    )
                
                await asyncio.sleep(self.system_metrics_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"System monitor error: {e}")
                await asyncio.sleep(self.system_metrics_interval)
    
    def _check_alerts(self, metrics: TaskMetrics) -> None:
        """检查任务相关的告警规则."""
        process_time = metrics.process_time_seconds or 0
        
        # 检查处理时间告警
        if process_time > 300:  # 5分钟
            self._trigger_alert(
                "task_duration",
                300.0,
                process_time,
                AlertSeverity.WARNING,
                "Long Processing Time",
                f"Task {metrics.task_id} took {process_time:.1f}s to process"
            )
        
        # 检查失败告警
        if not metrics.success:
            self._trigger_alert(
                "task_failure",
                1.0,
                1.0,
                AlertSeverity.ERROR,
                "Task Failed",
                f"Task {metrics.task_id} failed: {metrics.error_message}"
            )
    
    def _trigger_alert(
        self,
        metric_name: str,
        threshold: float,
        current_value: float,
        severity: AlertSeverity,
        title: str,
        message: str
    ) -> None:
        """触发告警."""
        import uuid
        
        alert = Alert(
            alert_id=str(uuid.uuid4())[:8],
            severity=severity,
            title=title,
            message=message,
            metric_name=metric_name,
            threshold=threshold,
            current_value=current_value
        )
        
        self._alerts.append(alert)
        
        # 调用处理器
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
        
        logger.warning(f"Alert triggered: {title}")
    
    def _find_in_completed(self, task_id: str) -> Optional[TaskMetrics]:
        """在已完成队列中查找任务."""
        for task in self._completed_tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def _parse_time_range(self, time_range: str) -> float:
        """解析时间范围."""
        if time_range.endswith("h"):
            return float(time_range[:-1]) * 3600
        elif time_range.endswith("d"):
            return float(time_range[:-1]) * 86400
        elif time_range.endswith("m"):
            return float(time_range[:-1]) * 60
        else:
            return 86400  # 默认24小时
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _load_history(self) -> None:
        """加载历史数据."""
        history_file = self.metrics_dir / "history.json"
        if not history_file.exists():
            return
        
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for task_data in data.get("completed_tasks", []):
                task = TaskMetrics(**task_data)
                self._completed_tasks.append(task)
            
            logger.info(f"Loaded {len(self._completed_tasks)} historical tasks")
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
    
    def _save_history(self) -> None:
        """保存历史数据."""
        history_file = self.metrics_dir / "history.json"
        
        try:
            data = {
                "saved_at": time.time(),
                "completed_tasks": [t.to_dict() for t in self._completed_tasks]
            }
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(self._completed_tasks)} tasks to history")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")


class _StageTimer:
    """阶段计时器上下文管理器."""
    
    def __init__(self, collector: MetricsCollector, task_id: str, stage_name: str):
        self.collector = collector
        self.task_id = task_id
        self.stage_name = stage_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.record_stage(self.task_id, self.stage_name, duration)


# 导入 asyncio 用于类型提示
import asyncio
