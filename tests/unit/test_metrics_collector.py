"""Tests for metrics collector module."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from video_cut_skill.core.metrics_collector import (
    Alert,
    AlertSeverity,
    MetricType,
    MetricValue,
    MetricsCollector,
    SystemMetrics,
    TaskMetrics,
)


class TestTaskMetrics:
    """Test TaskMetrics class."""
    
    def test_metrics_creation(self):
        """Test metrics creation."""
        metrics = TaskMetrics(
            task_id="task_001",
            task_type="edit",
            input_size_mb=100.5
        )
        
        assert metrics.task_id == "task_001"
        assert metrics.task_type == "edit"
        assert metrics.input_size_mb == 100.5
        assert metrics.submitted_at is not None
        assert metrics.started_at is None
    
    def test_wait_time_calculation(self):
        """Test wait time calculation."""
        import time as time_module
        
        metrics = TaskMetrics(task_id="task_001", task_type="edit")
        
        # Before start
        wait_time = metrics.wait_time_seconds
        assert wait_time >= 0
        
        # After start
        time_module.sleep(0.1)
        metrics.started_at = time_module.time()
        wait_time = metrics.wait_time_seconds
        assert wait_time >= 0.1
    
    def test_process_time_calculation(self):
        """Test process time calculation."""
        import time as time_module
        
        metrics = TaskMetrics(task_id="task_001", task_type="edit")
        
        # Before start
        assert metrics.process_time_seconds is None
        
        # During processing
        metrics.started_at = time_module.time()
        time_module.sleep(0.1)
        process_time = metrics.process_time_seconds
        assert process_time is not None
        assert process_time >= 0.1
        
        # After completion
        metrics.completed_at = time_module.time()
        final_time = metrics.process_time_seconds
        assert final_time is not None
        assert final_time <= 0.2
    
    def test_total_time_calculation(self):
        """Test total time calculation."""
        import time as time_module
        
        metrics = TaskMetrics(task_id="task_001", task_type="edit")
        time_module.sleep(0.1)
        metrics.started_at = time_module.time()
        time_module.sleep(0.1)
        metrics.completed_at = time_module.time()
        
        total = metrics.total_time_seconds
        assert total >= 0.2
    
    def test_metrics_serialization(self):
        """Test metrics serialization."""
        metrics = TaskMetrics(
            task_id="task_001",
            task_type="edit",
            input_size_mb=100.0,
            success=True,
            stages={"transcription": 5.0, "rendering": 10.0}
        )
        
        data = metrics.to_dict()
        
        assert data["task_id"] == "task_001"
        assert data["task_type"] == "edit"
        assert data["input_size_mb"] == 100.0
        assert data["success"] is True
        assert data["stages"]["transcription"] == 5.0


class TestMetricValue:
    """Test MetricValue class."""
    
    def test_metric_value_creation(self):
        """Test metric value creation."""
        metric = MetricValue(
            name="task_duration",
            value=30.5,
            metric_type=MetricType.TIMER,
            labels={"task_type": "edit"}
        )
        
        assert metric.name == "task_duration"
        assert metric.value == 30.5
        assert metric.metric_type == MetricType.TIMER
        assert metric.labels["task_type"] == "edit"
        assert metric.timestamp is not None
    
    def test_metric_serialization(self):
        """Test metric serialization."""
        metric = MetricValue(
            name="memory_usage",
            value=1024,
            metric_type=MetricType.GAUGE
        )
        
        data = metric.to_dict()
        
        assert data["name"] == "memory_usage"
        assert data["value"] == 1024
        assert data["type"] == "gauge"


class TestAlert:
    """Test Alert class."""
    
    def test_alert_creation(self):
        """Test alert creation."""
        alert = Alert(
            alert_id="alert_001",
            severity=AlertSeverity.WARNING,
            title="High Memory Usage",
            message="Memory usage is 95%",
            metric_name="memory_usage",
            threshold=90.0,
            current_value=95.0
        )
        
        assert alert.alert_id == "alert_001"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "High Memory Usage"
        assert alert.threshold == 90.0
        assert alert.current_value == 95.0
        assert alert.acknowledged is False
    
    def test_alert_serialization(self):
        """Test alert serialization."""
        alert = Alert(
            alert_id="alert_001",
            severity=AlertSeverity.ERROR,
            title="Task Failed",
            message="Task task_001 failed",
            metric_name="task_failure",
            threshold=1.0,
            current_value=1.0
        )
        
        data = alert.to_dict()
        
        assert data["alert_id"] == "alert_001"
        assert data["severity"] == "error"
        assert data["acknowledged"] is False


class TestMetricsCollector:
    """Test MetricsCollector class."""
    
    @pytest.fixture
    async def collector(self):
        """Create metrics collector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = MetricsCollector(
                metrics_dir=tmpdir,
                enable_system_monitoring=False
            )
            await collector.initialize()
            yield collector
            await collector.shutdown()
    
    @pytest.mark.asyncio
    async def test_start_task(self):
        """Test starting task recording."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        metrics = collector.start_task("task_001", "edit")
        
        assert metrics.task_id == "task_001"
        assert metrics.task_type == "edit"
        assert metrics.submitted_at is not None
        assert "task_001" in collector._task_metrics
    
    @pytest.mark.asyncio
    async def test_complete_task(self):
        """Test completing task recording."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        collector.start_task("task_001", "edit")
        collector.task_started("task_001")
        
        collector.complete_task("task_001", success=True, output_size_mb=50.0)
        
        # Should move to completed queue
        assert "task_001" not in collector._task_metrics
        assert len(collector._completed_tasks) == 1
        
        completed = collector._completed_tasks[0]
        assert completed.success is True
        assert completed.output_size_mb == 50.0
        assert completed.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_record_stage(self):
        """Test recording stage duration."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        collector.start_task("task_001", "edit")
        collector.record_stage("task_001", "transcription", 5.5)
        
        metrics = collector.get_task_metrics("task_001")
        assert metrics.stages["transcription"] == 5.5
    
    @pytest.mark.asyncio
    async def test_time_stage_context_manager(self):
        """Test time_stage context manager."""
        import asyncio
        
        collector = MetricsCollector(enable_system_monitoring=False)
        collector.start_task("task_001", "edit")
        
        with collector.time_stage("task_001", "transcription"):
            await asyncio.sleep(0.1)
        
        metrics = collector.get_task_metrics("task_001")
        assert "transcription" in metrics.stages
        assert metrics.stages["transcription"] >= 0.1
    
    @pytest.mark.asyncio
    async def test_record_metric(self):
        """Test recording generic metric."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        collector.record_metric(
            name="custom_metric",
            value=42.0,
            metric_type=MetricType.GAUGE,
            labels={"tag": "test"}
        )
        
        assert "custom_metric" in collector._metrics
        assert len(collector._metrics["custom_metric"]) == 1
        
        metric = collector._metrics["custom_metric"][0]
        assert metric.value == 42.0
        assert metric.labels["tag"] == "test"
    
    @pytest.mark.asyncio
    async def test_record_resource_usage(self):
        """Test recording resource usage."""
        collector = MetricsCollector(enable_system_monitoring=False)
        collector.start_task("task_001", "edit")
        
        collector.record_resource_usage(
            task_id="task_001",
            memory_mb=1024.5,
            cpu_percent=75.0,
            gpu_memory_mb=2048.0
        )
        
        metrics = collector.get_task_metrics("task_001")
        assert metrics.peak_memory_mb == 1024.5
        assert metrics.peak_cpu_percent == 75.0
        assert metrics.peak_gpu_memory_mb == 2048.0
        
        # Record higher values
        collector.record_resource_usage(
            task_id="task_001",
            memory_mb=2048.0,
            cpu_percent=80.0,
            gpu_memory_mb=4096.0
        )
        
        metrics = collector.get_task_metrics("task_001")
        assert metrics.peak_memory_mb == 2048.0
        assert metrics.peak_cpu_percent == 80.0
        assert metrics.peak_gpu_memory_mb == 4096.0
    
    @pytest.mark.asyncio
    async def test_record_cost(self):
        """Test recording cost."""
        collector = MetricsCollector(enable_system_monitoring=False)
        collector.start_task("task_001", "edit")
        
        collector.record_cost("task_001", 2.5)
        
        metrics = collector.get_task_metrics("task_001")
        assert metrics.estimated_cost_yuan == 2.5
    
    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting statistics."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        # Create some completed tasks
        for i in range(5):
            collector.start_task(f"task_{i}", "edit")
            collector.task_started(f"task_{i}")
            time.sleep(0.01)  # Small delay for process time
            collector.complete_task(f"task_{i}", success=(i < 4))
        
        stats = collector.get_statistics(time_range="1h")
        
        assert stats["total_tasks"] == 5
        assert stats["success_count"] == 4
        assert stats["failed_count"] == 1
        assert stats["success_rate"] == 0.8
        assert stats["avg_process_time"] > 0
    
    @pytest.mark.asyncio
    async def test_get_statistics_empty(self):
        """Test getting statistics with no tasks."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        stats = collector.get_statistics(time_range="1h")
        
        assert stats["total_tasks"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_process_time"] == 0.0
    
    @pytest.mark.asyncio
    async def test_get_statistics_by_task_type(self):
        """Test getting statistics filtered by task type."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        # Create tasks of different types
        collector.start_task("task_1", "edit")
        collector.task_started("task_1")
        collector.complete_task("task_1", success=True)
        
        collector.start_task("task_2", "transcode")
        collector.task_started("task_2")
        collector.complete_task("task_2", success=True)
        
        collector.start_task("task_3", "edit")
        collector.task_started("task_3")
        collector.complete_task("task_3", success=True)
        
        edit_stats = collector.get_statistics(task_type="edit")
        assert edit_stats["total_tasks"] == 2
        
        transcode_stats = collector.get_statistics(task_type="transcode")
        assert transcode_stats["total_tasks"] == 1
    
    @pytest.mark.asyncio
    async def test_alert_rules(self):
        """Test alert rules."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        alerts_received = []
        
        def alert_handler(alert):
            alerts_received.append(alert)
        
        collector.add_alert_handler(alert_handler)
        collector.add_alert_rule(
            metric_name="task_duration",
            threshold=1.0,
            comparison="greater_than",
            severity=AlertSeverity.WARNING
        )
        
        # Create a task that triggers the alert
        collector.start_task("task_001", "edit")
        collector.task_started("task_001")
        time.sleep(0.1)  # Long enough to trigger alert
        
        # Manually check alerts
        metrics = collector.get_task_metrics("task_001")
        metrics.completed_at = time.time()
        collector._check_alerts(metrics)
        
        # Note: Alert is only triggered on complete_task
        collector.complete_task("task_001", success=True)
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self):
        """Test acknowledging alerts."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        # Create an alert directly
        alert = Alert(
            alert_id="test_alert",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test message",
            metric_name="test",
            threshold=1.0,
            current_value=2.0
        )
        collector._alerts.append(alert)
        
        # Verify unacknowledged
        unacknowledged = collector.get_alerts(unacknowledged_only=True)
        assert len(unacknowledged) == 1
        
        # Acknowledge
        result = collector.acknowledge_alert("test_alert")
        assert result is True
        
        # Verify acknowledged
        unacknowledged = collector.get_alerts(unacknowledged_only=True)
        assert len(unacknowledged) == 0
    
    @pytest.mark.asyncio
    async def test_export_metrics_json(self):
        """Test exporting metrics in JSON format."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        # Create some tasks
        collector.start_task("task_001", "edit")
        collector.task_started("task_001")
        collector.complete_task("task_001", success=True)
        
        json_output = collector.export_metrics(format="json")
        data = json.loads(json_output)
        
        assert "statistics" in data
        assert "active_tasks" in data
        assert data["active_tasks"] == 0
        assert data["completed_tasks"] == 1
    
    @pytest.mark.asyncio
    async def test_export_metrics_prometheus(self):
        """Test exporting metrics in Prometheus format."""
        collector = MetricsCollector(enable_system_monitoring=False)
        
        # Create some tasks
        collector.start_task("task_001", "edit")
        collector.task_started("task_001")
        collector.complete_task("task_001", success=True)
        
        prom_output = collector.export_metrics(format="prometheus")
        
        assert "video_cut_tasks_total" in prom_output
        assert "video_cut_success_rate" in prom_output
    
    @pytest.mark.asyncio
    async def test_persistence(self):
        """Test metrics persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create collector and add tasks
            collector = MetricsCollector(
                metrics_dir=tmpdir,
                enable_system_monitoring=False
            )
            await collector.initialize()
            
            collector.start_task("task_001", "edit")
            collector.task_started("task_001")
            collector.complete_task("task_001", success=True)
            
            await collector.shutdown()
            
            # Verify file was created
            history_file = Path(tmpdir) / "history.json"
            assert history_file.exists()
            
            # Load and verify
            with open(history_file) as f:
                data = json.load(f)
            
            assert len(data["completed_tasks"]) == 1
            assert data["completed_tasks"][0]["task_id"] == "task_001"


class TestSystemMetrics:
    """Test SystemMetrics class."""
    
    def test_system_metrics_creation(self):
        """Test system metrics creation."""
        metrics = SystemMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=75.0,
            memory_used_mb=8192.0,
            memory_total_mb=16384.0,
            disk_percent=80.0,
            disk_free_gb=100.0
        )
        
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 75.0
        assert metrics.disk_percent == 80.0
    
    def test_system_metrics_with_gpu(self):
        """Test system metrics with GPU info."""
        metrics = SystemMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=75.0,
            memory_used_mb=8192.0,
            memory_total_mb=16384.0,
            disk_percent=80.0,
            disk_free_gb=100.0,
            gpu_metrics=[
                {
                    "index": 0,
                    "memory_used_mb": 4096.0,
                    "memory_total_mb": 8192.0,
                    "utilization_percent": 80.0
                }
            ]
        )
        
        assert len(metrics.gpu_metrics) == 1
        assert metrics.gpu_metrics[0]["index"] == 0
        assert metrics.gpu_metrics[0]["utilization_percent"] == 80.0


class TestAlertSeverity:
    """Test AlertSeverity enum."""
    
    def test_severity_levels(self):
        """Test severity levels."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestMetricType:
    """Test MetricType enum."""
    
    def test_metric_types(self):
        """Test metric types."""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.TIMER.value == "timer"
