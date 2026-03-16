# P0 功能使用示例

本文档演示如何使用 v0.4.2 新增的 P0 核心功能：

1. **TaskQueue** - 任务队列与并发控制
2. **CheckpointManager** - 断点续传
3. **MetricsCollector** - 性能监控

---

## TaskQueue - 任务队列

### 基本用法

```python
import asyncio
from video_cut_skill import TaskQueue, VideoTask, TaskPriority

async def main():
    # 创建队列（最大并发2个任务，队列长度10）
    queue = TaskQueue(
        max_concurrent=2,
        max_queue_size=10,
        timeout_seconds=3600,
        retry_count=2
    )
    
    # 初始化队列
    await queue.initialize()
    
    # 创建视频编辑任务
    task = VideoTask(
        task_type="edit",
        input_path="/path/to/input.mp4",
        output_path="/path/to/output.mp4",
        params={
            "target_duration": 60,
            "aspect_ratio": "9:16",
            "add_subtitles": True
        },
        priority=TaskPriority.HIGH
    )
    
    # 提交任务
    task_id = await queue.submit(task)
    print(f"Task submitted: {task_id}")
    
    # 查询任务状态
    status = await queue.get_status(task_id)
    print(f"Status: {status.status.value}")
    
    # 等待任务完成
    result = await queue.wait_for_completion(task_id)
    print(f"Completed! Output: {result}")
    
    # 关闭队列
    await queue.shutdown()

asyncio.run(main())
```

### 批量提交任务

```python
async def batch_process():
    queue = TaskQueue(max_concurrent=2)
    await queue.initialize()
    
    videos = ["video1.mp4", "video2.mp4", "video3.mp4"]
    task_ids = []
    
    # 批量提交
    for video in videos:
        task = VideoTask(
            task_type="edit",
            input_path=video,
            priority=TaskPriority.NORMAL
        )
        task_id = await queue.submit(task)
        task_ids.append(task_id)
    
    # 等待所有任务完成
    for task_id in task_ids:
        result = await queue.wait_for_completion(task_id)
        print(f"Task {task_id} completed")
    
    await queue.shutdown()
```

### 设置回调函数

```python
async def process_with_callbacks():
    queue = TaskQueue(max_concurrent=2)
    
    # 设置回调函数
    def on_task_start(task):
        print(f"[START] {task.task_id}")
    
    def on_task_complete(task):
        print(f"[COMPLETE] {task.task_id}, duration: {task.duration:.1f}s")
    
    def on_task_failed(task):
        print(f"[FAILED] {task.task_id}, error: {task.error_message}")
    
    def on_progress(task_id, progress):
        percentage = progress * 100
        print(f"[PROGRESS] {task_id}: {percentage:.1f}%")
    
    queue.set_callbacks(
        on_task_start=on_task_start,
        on_task_complete=on_task_complete,
        on_task_failed=on_task_failed,
        on_progress=on_progress
    )
    
    await queue.initialize()
    
    # 提交任务...
    task = VideoTask(task_type="edit", input_path="input.mp4")
    await queue.submit(task)
    
    await queue.shutdown()
```

### 获取队列统计

```python
async def monitor_queue():
    queue = TaskQueue(max_concurrent=2)
    await queue.initialize()
    
    # 提交一些任务...
    
    # 获取统计信息
    stats = await queue.get_stats()
    print(f"Pending: {stats.total_pending}")
    print(f"Running: {stats.total_running}")
    print(f"Completed: {stats.total_completed}")
    print(f"Failed: {stats.total_failed}")
    print(f"Avg wait time: {stats.avg_wait_time:.1f}s")
    print(f"Avg process time: {stats.avg_process_time:.1f}s")
```

---

## CheckpointManager - 断点续传

### 基本用法

```python
from video_cut_skill import CheckpointManager, ProcessingStage

async def process_with_checkpoints():
    # 创建检查点管理器
    manager = CheckpointManager(
        checkpoint_dir="~/.video_cut_skill/checkpoints"
    )
    
    task_id = "task_001"
    input_path = "/path/to/long_video.mp4"
    
    # 检查是否可以恢复
    if manager.can_resume(task_id):
        print("Resuming from checkpoint...")
        checkpoint = manager.load_checkpoint(task_id)
        resume_stage = manager.get_resume_stage(checkpoint)
        print(f"Resuming from: {resume_stage.value}")
    else:
        # 创建新检查点
        checkpoint = manager.create_checkpoint(
            task_id=task_id,
            input_path=input_path,
            output_path="/path/to/output.mp4",
            params={"target_duration": 300}
        )
        resume_stage = ProcessingStage.INITIALIZED
    
    try:
        # 阶段 1: 转录
        if resume_stage.value <= ProcessingStage.TRANSCRIPTION_COMPLETE.value:
            print("Starting transcription...")
            transcript = await transcribe_video(input_path)
            
            # 保存检查点
            manager.save_stage_checkpoint(
                task_id=task_id,
                stage=ProcessingStage.TRANSCRIPTION_COMPLETE,
                data={"transcript": transcript},
                metadata={"model": "whisper-large"}
            )
            print("Transcription checkpoint saved")
        else:
            # 从检查点加载
            cp_data = checkpoint.get_stage_checkpoint(
                ProcessingStage.TRANSCRIPTION_COMPLETE
            )
            transcript = cp_data.data["transcript"]
            print("Loaded transcript from checkpoint")
        
        # 阶段 2: 分析
        if resume_stage.value <= ProcessingStage.ANALYSIS_COMPLETE.value:
            print("Starting analysis...")
            analysis = await analyze_content(transcript)
            
            manager.save_stage_checkpoint(
                task_id=task_id,
                stage=ProcessingStage.ANALYSIS_COMPLETE,
                data={"analysis": analysis}
            )
        
        # 阶段 3: 渲染（支持帧级别进度）
        if resume_stage.value <= ProcessingStage.RENDERING.value:
            print("Starting rendering...")
            
            total_frames = 10000
            start_frame = checkpoint.rendered_frames if checkpoint else 0
            
            for frame in range(start_frame, total_frames):
                await render_frame(frame)
                
                # 每100帧更新一次检查点
                if frame % 100 == 0:
                    manager.update_rendering_progress(
                        task_id=task_id,
                        rendered_frames=frame,
                        total_frames=total_frames
                    )
            
            manager.save_stage_checkpoint(
                task_id=task_id,
                stage=ProcessingStage.RENDERING_COMPLETE,
                data={}
            )
        
        # 标记完成
        manager.save_stage_checkpoint(
            task_id=task_id,
            stage=ProcessingStage.COMPLETED,
            data={"output_path": checkpoint.output_path}
        )
        
        print("Processing completed!")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        print("Progress saved. You can resume later.")
        raise
```

### 查看检查点列表

```python
def list_checkpoints():
    manager = CheckpointManager()
    
    # 列出所有检查点
    all_checkpoints = manager.list_checkpoints()
    print(f"Total checkpoints: {len(all_checkpoints)}")
    
    for cp in all_checkpoints:
        print(f"\nTask: {cp.task_id}")
        print(f"  Stage: {cp.current_stage.value}")
        print(f"  Progress: {cp.progress * 100:.1f}%")
        print(f"  Updated: {datetime.fromtimestamp(cp.updated_at)}")
    
    # 只列出已完成的
    completed = manager.list_checkpoints(status=ProcessingStage.COMPLETED)
    print(f"\nCompleted tasks: {len(completed)}")
    
    # 只列出渲染中的
    rendering = manager.list_checkpoints(status=ProcessingStage.RENDERING)
    print(f"Rendering tasks: {len(rendering)}")
```

### 清理旧检查点

```python
def cleanup():
    manager = CheckpointManager()
    
    # 清理7天前的检查点
    deleted = manager.cleanup_old_checkpoints(max_age_days=7)
    print(f"Deleted {deleted} old checkpoints")
    
    # 删除特定任务的检查点
    manager.delete_checkpoint("task_001")
    print("Deleted checkpoint for task_001")
```

---

## MetricsCollector - 性能监控

### 基本用法

```python
from video_cut_skill import MetricsCollector

async def monitor_processing():
    # 创建监控器
    collector = MetricsCollector(
        metrics_dir="~/.video_cut_skill/metrics",
        enable_system_monitoring=True
    )
    
    await collector.initialize()
    
    # 开始记录任务
    task_id = "task_001"
    collector.start_task(task_id, task_type="edit")
    
    # 标记任务开始处理
    collector.task_started(task_id)
    
    try:
        # 阶段 1: 转录（自动计时）
        with collector.time_stage(task_id, "transcription"):
            transcript = await transcribe_video(input_path)
        
        # 阶段 2: 分析
        with collector.time_stage(task_id, "analysis"):
            analysis = await analyze_content(transcript)
        
        # 阶段 3: 渲染
        with collector.time_stage(task_id, "rendering"):
            output = await render_video(analysis)
        
        # 记录资源使用峰值
        collector.record_resource_usage(
            task_id=task_id,
            memory_mb=2048.5,
            cpu_percent=85.0,
            gpu_memory_mb=4096.0
        )
        
        # 记录成本
        collector.record_cost(task_id, cost_yuan=2.5)
        
        # 标记任务完成
        collector.complete_task(
            task_id=task_id,
            success=True,
            output_size_mb=50.0
        )
        
    except Exception as e:
        collector.complete_task(
            task_id=task_id,
            success=False,
            error_message=str(e)
        )
        raise
    
    await collector.shutdown()
```

### 手动记录指标

```python
def record_custom_metrics():
    collector = MetricsCollector()
    
    # 记录各种指标
    collector.record_metric(
        name="custom_counter",
        value=1,
        metric_type=MetricType.COUNTER,
        labels={"operation": "upload"}
    )
    
    collector.record_metric(
        name="memory_usage",
        value=1024.5,
        metric_type=MetricType.GAUGE,
        labels={"task_id": "task_001"}
    )
    
    collector.record_metric(
        name="processing_duration",
        value=30.5,
        metric_type=MetricType.TIMER,
        labels={"stage": "transcription"}
    )
```

### 获取统计信息

```python
def print_statistics():
    collector = MetricsCollector()
    
    # 获取最近24小时的统计
    stats = collector.get_statistics(time_range="24h")
    
    print("=== Processing Statistics (24h) ===")
    print(f"Total tasks: {stats['total_tasks']}")
    print(f"Success rate: {stats['success_rate'] * 100:.1f}%")
    print(f"Failed count: {stats['failed_count']}")
    print()
    print(f"Avg process time: {stats['avg_process_time']:.1f}s")
    print(f"P95 process time: {stats['p95_process_time']:.1f}s")
    print(f"P99 process time: {stats['p99_process_time']:.1f}s")
    print()
    print(f"Avg wait time: {stats['avg_wait_time']:.1f}s")
    print(f"Total cost: ¥{stats['total_cost_yuan']:.2f}")
    
    # 按任务类型统计
    edit_stats = collector.get_statistics(
        time_range="24h",
        task_type="edit"
    )
    print(f"\nEdit tasks: {edit_stats['total_tasks']}")
```

### 配置告警

```python
async def setup_alerts():
    collector = MetricsCollector()
    await collector.initialize()
    
    # 添加告警规则
    collector.add_alert_rule(
        metric_name="task_duration",
        threshold=300,  # 5分钟
        comparison="greater_than",
        severity=AlertSeverity.WARNING,
        title="Long Processing Time",
        message_template="Task {task_id} took {value}s to process"
    )
    
    collector.add_alert_rule(
        metric_name="memory_usage",
        threshold=8192,  # 8GB
        comparison="greater_than",
        severity=AlertSeverity.ERROR,
        title="High Memory Usage",
        message_template="Memory usage exceeded {threshold}MB: {value}MB"
    )
    
    # 添加告警处理器
    def send_email_alert(alert):
        print(f"[ALERT EMAIL] {alert.severity.value}: {alert.title}")
        print(f"  {alert.message}")
    
    def send_slack_alert(alert):
        print(f"[ALERT SLACK] {alert.severity.value}: {alert.title}")
    
    collector.add_alert_handler(send_email_alert)
    collector.add_alert_handler(send_slack_alert)
    
    # 查看未确认的告警
    alerts = collector.get_alerts(unacknowledged_only=True)
    print(f"Unacknowledged alerts: {len(alerts)}")
    
    # 确认告警
    for alert in alerts:
        collector.acknowledge_alert(alert.alert_id)
```

### 导出指标

```python
def export_metrics():
    collector = MetricsCollector()
    
    # 导出为 JSON
    json_metrics = collector.export_metrics(format="json")
    with open("metrics.json", "w") as f:
        f.write(json_metrics)
    
    # 导出为 Prometheus 格式
    prom_metrics = collector.export_metrics(format="prometheus")
    with open("metrics.prom", "w") as f:
        f.write(prom_metrics)
```

### 获取系统指标

```python
def monitor_system():
    collector = MetricsCollector(enable_system_monitoring=True)
    
    # 获取最近的系统指标
    system_metrics = collector.get_system_metrics(limit=10)
    
    for metric in system_metrics:
        print(f"Time: {datetime.fromtimestamp(metric.timestamp)}")
        print(f"  CPU: {metric.cpu_percent:.1f}%")
        print(f"  Memory: {metric.memory_percent:.1f}% ({metric.memory_used_mb:.0f}MB / {metric.memory_total_mb:.0f}MB)")
        print(f"  Disk: {metric.disk_percent:.1f}% ({metric.disk_free_gb:.1f}GB free)")
        
        for gpu in metric.gpu_metrics:
            print(f"  GPU {gpu['index']}: {gpu['utilization_percent']:.1f}% "
                  f"({gpu['memory_used_mb']:.0f}MB / {gpu['memory_total_mb']:.0f}MB)")
```

---

## 完整集成示例

```python
"""完整示例：使用 TaskQueue + CheckpointManager + MetricsCollector"""

import asyncio
from video_cut_skill import (
    TaskQueue, VideoTask, TaskPriority,
    CheckpointManager, ProcessingStage,
    MetricsCollector
)

async def robust_video_processing():
    """健壮的视频处理流程，支持并发控制、断点续传和性能监控."""
    
    # 初始化所有组件
    queue = TaskQueue(max_concurrent=2, max_queue_size=10)
    checkpoint_manager = CheckpointManager()
    metrics_collector = MetricsCollector(enable_system_monitoring=True)
    
    await queue.initialize()
    await metrics_collector.initialize()
    
    # 设置队列回调，记录到监控器
    def on_task_start(task):
        metrics_collector.task_started(task.task_id)
    
    def on_task_complete(task):
        metrics_collector.complete_task(
            task_id=task.task_id,
            success=True,
            output_size_mb=task.result.get("output_size_mb", 0) if task.result else 0
        )
    
    def on_task_failed(task):
        metrics_collector.complete_task(
            task_id=task.task_id,
            success=False,
            error_message=task.error_message
        )
    
    queue.set_callbacks(
        on_task_start=on_task_start,
        on_task_complete=on_task_complete,
        on_task_failed=on_task_failed
    )
    
    try:
        # 提交任务
        task = VideoTask(
            task_type="edit",
            input_path="long_video.mp4",
            output_path="output.mp4",
            params={"target_duration": 300},
            priority=TaskPriority.HIGH
        )
        
        task_id = await queue.submit(task)
        print(f"Task {task_id} submitted")
        
        # 等待完成
        result = await queue.wait_for_completion(task_id)
        print(f"Task completed: {result}")
        
        # 打印统计
        stats = metrics_collector.get_statistics(time_range="1h")
        print(f"\nStatistics:")
        print(f"  Success rate: {stats['success_rate'] * 100:.1f}%")
        print(f"  Avg time: {stats['avg_process_time']:.1f}s")
        
    finally:
        await queue.shutdown()
        await metrics_collector.shutdown()

if __name__ == "__main__":
    asyncio.run(robust_video_processing())
```

---

## 配置示例

```yaml
# video_cut_skill.yaml
queue:
  max_concurrent: 2              # 最大并发任务数
  max_queue_size: 10             # 队列最大长度
  timeout_seconds: 3600          # 任务超时时间
  retry_count: 2                 # 失败重试次数
  retry_delay_seconds: 30        # 重试间隔
  persistence_enabled: true      # 是否持久化

cost_control:
  max_video_duration_minutes: 30
  max_cost_yuan: 3.0
  cache_enabled: true

session:
  persistence_enabled: true
  cache_dir: ~/.video_cut_skill
```
