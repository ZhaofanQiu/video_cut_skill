"""Tests for task queue module."""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from video_cut_skill.core.task_queue import (
    QueueStats,
    TaskPriority,
    TaskQueue,
    TaskStatus,
    VideoTask,
)


class TestVideoTask:
    """Test VideoTask class."""
    
    def test_task_creation(self):
        """Test task creation."""
        task = VideoTask(
            task_type="edit",
            input_path="/path/to/input.mp4",
            output_path="/path/to/output.mp4",
            params={"target_duration": 60}
        )
        
        assert task.task_type == "edit"
        assert task.input_path == "/path/to/input.mp4"
        assert task.output_path == "/path/to/output.mp4"
        assert task.params["target_duration"] == 60
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL
        assert task.task_id is not None
        assert task.created_at is not None
    
    def test_task_serialization(self):
        """Test task serialization."""
        task = VideoTask(
            task_type="edit",
            input_path="input.mp4",
            priority=TaskPriority.HIGH
        )
        
        data = task.to_dict()
        restored = VideoTask.from_dict(data)
        
        assert restored.task_type == task.task_type
        assert restored.input_path == task.input_path
        assert restored.priority == task.priority
        assert restored.task_id == task.task_id
    
    def test_task_duration(self):
        """Test task duration calculation."""
        import time
        
        task = VideoTask(task_type="edit", input_path="input.mp4")
        
        # Before start
        assert task.duration is None
        
        # During processing
        task.started_at = time.time() - 5
        assert task.duration is not None
        assert task.duration >= 5
        
        # After completion
        task.completed_at = time.time()
        duration = task.duration
        assert duration is not None
        assert duration <= 5.1  # Allow small variance


class TestTaskQueue:
    """Test TaskQueue class."""
    
    @pytest.fixture
    async def queue(self):
        """Create and initialize queue."""
        q = TaskQueue(
            max_concurrent=2,
            max_queue_size=5,
            timeout_seconds=60
        )
        await q.initialize()
        yield q
        await q.shutdown(wait_for_pending=False)
    
    @pytest.mark.asyncio
    async def test_submit_and_retrieve(self):
        """Test task submission and retrieval."""
        queue = TaskQueue(max_concurrent=1, max_queue_size=5)
        await queue.initialize()
        
        task = VideoTask(task_type="edit", input_path="input.mp4")
        task_id = await queue.submit(task)
        
        assert task_id == task.task_id
        
        retrieved = await queue.get_status(task_id)
        assert retrieved is not None
        assert retrieved.task_id == task_id
        
        await queue.shutdown(wait_for_pending=False)
    
    @pytest.mark.asyncio
    async def test_queue_full(self):
        """Test queue full behavior."""
        queue = TaskQueue(max_concurrent=1, max_queue_size=1)
        await queue.initialize()
        
        # Fill the queue
        task1 = VideoTask(task_type="edit", input_path="input1.mp4")
        await queue.submit(task1, block=False)
        
        task2 = VideoTask(task_type="edit", input_path="input2.mp4")
        
        # Should raise QueueFull when block=False
        with pytest.raises(asyncio.QueueFull):
            await queue.submit(task2, block=False)
        
        await queue.shutdown(wait_for_pending=False)
    
    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test task cancellation."""
        queue = TaskQueue(max_concurrent=1, max_queue_size=5)
        await queue.initialize()
        
        task = VideoTask(task_type="edit", input_path="input.mp4")
        task_id = await queue.submit(task)
        
        # Cancel pending task
        cancelled = await queue.cancel_task(task_id)
        assert cancelled is True
        
        status = await queue.get_status(task_id)
        assert status.status == TaskStatus.CANCELLED
        
        await queue.shutdown(wait_for_pending=False)
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test queue statistics."""
        queue = TaskQueue(max_concurrent=1, max_queue_size=5)
        await queue.initialize()
        
        # Submit some tasks
        for i in range(3):
            task = VideoTask(task_type="edit", input_path=f"input{i}.mp4")
            await queue.submit(task)
        
        stats = await queue.get_stats()
        
        assert isinstance(stats, QueueStats)
        assert stats.total_pending >= 0
        assert stats.total_running >= 0
        
        await queue.shutdown(wait_for_pending=False)
    
    @pytest.mark.asyncio
    async def test_persistence(self):
        """Test queue state persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence_path = Path(tmpdir) / "queue_state.json"
            
            # Create queue and submit task
            queue = TaskQueue(
                max_concurrent=1,
                max_queue_size=5,
                persistence_path=str(persistence_path)
            )
            await queue.initialize()
            
            task = VideoTask(task_type="edit", input_path="input.mp4")
            task_id = await queue.submit(task)
            
            # Shutdown to trigger save
            await queue.shutdown(wait_for_pending=False)
            
            # Verify state was saved
            assert persistence_path.exists()
            
            with open(persistence_path) as f:
                state = json.load(f)
            
            assert task_id in state["tasks"]
    
    @pytest.mark.asyncio
    async def test_callbacks(self):
        """Test task callbacks."""
        queue = TaskQueue(max_concurrent=1, max_queue_size=5)
        
        callbacks_received = []
        
        def on_start(task):
            callbacks_received.append(("start", task.task_id))
        
        def on_complete(task):
            callbacks_received.append(("complete", task.task_id))
        
        queue.set_callbacks(on_task_start=on_start, on_task_complete=on_complete)
        
        await queue.initialize()
        
        # Override process task to complete immediately
        async def mock_process(task):
            return {"result": "ok"}
        
        queue._process_task = mock_process
        
        task = VideoTask(task_type="edit", input_path="input.mp4")
        task_id = await queue.submit(task)
        
        # Wait for task to complete
        await queue.wait_for_completion(task_id, timeout=5)
        
        # Wait a bit for callbacks
        await asyncio.sleep(0.1)
        
        assert len(callbacks_received) == 2
        assert callbacks_received[0][0] == "start"
        assert callbacks_received[1][0] == "complete"
        
        await queue.shutdown(wait_for_pending=False)
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test task priority ordering."""
        queue = TaskQueue(max_concurrent=1, max_queue_size=5)
        await queue.initialize()
        
        execution_order = []
        
        async def mock_process(task):
            execution_order.append((task.priority, task.task_id))
            return {"result": "ok"}
        
        queue._process_task = mock_process
        
        # Submit tasks in reverse priority order
        tasks = []
        for priority in [TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH]:
            task = VideoTask(
                task_type="edit",
                input_path="input.mp4",
                priority=priority
            )
            tasks.append(task)
            await queue.submit(task)
        
        # Wait for all tasks
        for task in tasks:
            await queue.wait_for_completion(task.task_id, timeout=5)
        
        await asyncio.sleep(0.1)
        
        # Check execution order (HIGH should be first)
        priorities = [p for p, _ in execution_order]
        assert priorities[0] == TaskPriority.HIGH
        
        await queue.shutdown(wait_for_pending=False)


class TestQueueStats:
    """Test QueueStats class."""
    
    def test_stats_creation(self):
        """Test stats creation."""
        stats = QueueStats(
            total_pending=5,
            total_running=2,
            total_completed=10,
            total_failed=1,
            avg_wait_time=10.5,
            avg_process_time=30.0
        )
        
        assert stats.total_pending == 5
        assert stats.total_running == 2
        assert stats.total_completed == 10
        assert stats.total_failed == 1
        assert stats.avg_wait_time == 10.5
        assert stats.avg_process_time == 30.0
    
    def test_stats_serialization(self):
        """Test stats serialization."""
        stats = QueueStats(total_pending=3, total_running=1)
        data = stats.to_dict()
        
        assert data["total_pending"] == 3
        assert data["total_running"] == 1
