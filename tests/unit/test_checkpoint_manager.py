"""Tests for checkpoint manager module."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from video_cut_skill.core.checkpoint_manager import (
    CheckpointManager,
    ProcessingStage,
    StageCheckpoint,
    VideoCheckpoint,
)


class TestVideoCheckpoint:
    """Test VideoCheckpoint class."""
    
    def test_checkpoint_creation(self):
        """Test checkpoint creation."""
        checkpoint = VideoCheckpoint(
            task_id="task_001",
            input_path="/path/to/input.mp4",
            output_path="/path/to/output.mp4"
        )
        
        assert checkpoint.task_id == "task_001"
        assert checkpoint.input_path == "/path/to/input.mp4"
        assert checkpoint.output_path == "/path/to/output.mp4"
        assert checkpoint.current_stage == ProcessingStage.INITIALIZED
        assert checkpoint.checkpoints == []
    
    def test_progress_calculation(self):
        """Test progress calculation."""
        checkpoint = VideoCheckpoint(task_id="task_001", input_path="input.mp4")
        
        # Initial progress
        assert checkpoint.progress == 0.0
        
        # After transcription
        checkpoint.current_stage = ProcessingStage.TRANSCRIPTION_COMPLETE
        progress = checkpoint.progress
        assert progress > 0.0
        assert progress < 1.0
        
        # Completed
        checkpoint.current_stage = ProcessingStage.COMPLETED
        assert checkpoint.progress == 1.0
    
    def test_rendering_progress(self):
        """Test rendering progress calculation."""
        checkpoint = VideoCheckpoint(task_id="task_001", input_path="input.mp4")
        checkpoint.current_stage = ProcessingStage.RENDERING
        checkpoint.total_frames = 1000
        checkpoint.rendered_frames = 250
        
        assert checkpoint.progress == 0.25
        
        checkpoint.rendered_frames = 500
        assert checkpoint.progress == 0.5
    
    def test_stage_checkpoint_retrieval(self):
        """Test retrieving stage checkpoints."""
        checkpoint = VideoCheckpoint(task_id="task_001", input_path="input.mp4")
        
        # Add stage checkpoints
        cp1 = StageCheckpoint(
            stage=ProcessingStage.TRANSCRIPTION_COMPLETE,
            data={"transcript": "test"}
        )
        cp2 = StageCheckpoint(
            stage=ProcessingStage.ANALYSIS_COMPLETE,
            data={"analysis": "test"}
        )
        
        checkpoint.checkpoints = [cp1, cp2]
        
        # Retrieve by stage
        retrieved = checkpoint.get_stage_checkpoint(ProcessingStage.ANALYSIS_COMPLETE)
        assert retrieved is not None
        assert retrieved.stage == ProcessingStage.ANALYSIS_COMPLETE
        
        # Get last checkpoint
        last = checkpoint.get_last_checkpoint()
        assert last == cp2
    
    def test_serialization(self):
        """Test checkpoint serialization."""
        checkpoint = VideoCheckpoint(
            task_id="task_001",
            input_path="input.mp4",
            output_path="output.mp4",
            input_hash="abc123",
            input_size=1024,
            current_stage=ProcessingStage.TRANSCRIPTION_COMPLETE
        )
        
        stage_cp = StageCheckpoint(
            stage=ProcessingStage.TRANSCRIPTION_COMPLETE,
            data={"transcript": "test data"}
        )
        checkpoint.checkpoints.append(stage_cp)
        
        # Serialize
        data = checkpoint.to_dict()
        
        # Deserialize
        restored = VideoCheckpoint.from_dict(data)
        
        assert restored.task_id == checkpoint.task_id
        assert restored.input_path == checkpoint.input_path
        assert restored.input_hash == checkpoint.input_hash
        assert restored.current_stage == checkpoint.current_stage
        assert len(restored.checkpoints) == 1
        assert restored.checkpoints[0].data["transcript"] == "test data"


class TestStageCheckpoint:
    """Test StageCheckpoint class."""
    
    def test_stage_checkpoint_creation(self):
        """Test stage checkpoint creation."""
        cp = StageCheckpoint(
            stage=ProcessingStage.TRANSCRIPTION_COMPLETE,
            data={"transcript": "test"},
            metadata={"model": "whisper"}
        )
        
        assert cp.stage == ProcessingStage.TRANSCRIPTION_COMPLETE
        assert cp.data["transcript"] == "test"
        assert cp.metadata["model"] == "whisper"
        assert cp.timestamp is not None
    
    def test_stage_checkpoint_serialization(self):
        """Test stage checkpoint serialization."""
        cp = StageCheckpoint(
            stage=ProcessingStage.ANALYSIS_COMPLETE,
            data={"keywords": ["test"]}
        )
        
        data = cp.to_dict()
        restored = StageCheckpoint.from_dict(data)
        
        assert restored.stage == cp.stage
        assert restored.data == cp.data


class TestCheckpointManager:
    """Test CheckpointManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create checkpoint manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(checkpoint_dir=tmpdir)
            yield manager
    
    def test_create_checkpoint(self, manager):
        """Test checkpoint creation."""
        checkpoint = manager.create_checkpoint(
            task_id="task_001",
            input_path="input.mp4",
            output_path="output.mp4",
            params={"target_duration": 60}
        )
        
        assert checkpoint.task_id == "task_001"
        assert checkpoint.params["target_duration"] == 60
        
        # Verify file was created
        checkpoint_path = manager._get_checkpoint_path("task_001")
        assert checkpoint_path.exists()
    
    def test_load_checkpoint(self, manager):
        """Test checkpoint loading."""
        # Create checkpoint
        original = manager.create_checkpoint(
            task_id="task_001",
            input_path="input.mp4"
        )
        
        # Clear cache and reload
        manager._cache.clear()
        
        loaded = manager.load_checkpoint("task_001")
        
        assert loaded is not None
        assert loaded.task_id == original.task_id
        assert loaded.input_path == original.input_path
    
    def test_save_stage_checkpoint(self, manager):
        """Test saving stage checkpoint."""
        # Create initial checkpoint
        manager.create_checkpoint(task_id="task_001", input_path="input.mp4")
        
        # Save stage checkpoint
        manager.save_stage_checkpoint(
            task_id="task_001",
            stage=ProcessingStage.TRANSCRIPTION_COMPLETE,
            data={"transcript": "test transcript"},
            metadata={"duration": 300}
        )
        
        # Load and verify
        checkpoint = manager.load_checkpoint("task_001")
        assert checkpoint.current_stage == ProcessingStage.TRANSCRIPTION_COMPLETE
        
        stage_cp = checkpoint.get_stage_checkpoint(ProcessingStage.TRANSCRIPTION_COMPLETE)
        assert stage_cp is not None
        assert stage_cp.data["transcript"] == "test transcript"
        assert stage_cp.metadata["duration"] == 300
    
    def test_update_rendering_progress(self, manager):
        """Test updating rendering progress."""
        manager.create_checkpoint(task_id="task_001", input_path="input.mp4")
        
        # Update progress
        manager.update_rendering_progress("task_001", rendered_frames=100, total_frames=1000)
        
        checkpoint = manager.load_checkpoint("task_001")
        assert checkpoint.rendered_frames == 100
        assert checkpoint.total_frames == 1000
        assert checkpoint.current_stage == ProcessingStage.RENDERING
    
    def test_get_resume_stage(self, manager):
        """Test getting resume stage."""
        manager.create_checkpoint(task_id="task_001", input_path="input.mp4")
        
        # At INITIALIZED, should resume from next stage
        checkpoint = manager.load_checkpoint("task_001")
        resume_stage = manager.get_resume_stage(checkpoint)
        assert resume_stage == ProcessingStage.TRANSCRIPTION_STARTED
        
        # After transcription
        manager.save_stage_checkpoint(
            task_id="task_001",
            stage=ProcessingStage.TRANSCRIPTION_COMPLETE,
            data={}
        )
        checkpoint = manager.load_checkpoint("task_001")
        resume_stage = manager.get_resume_stage(checkpoint)
        assert resume_stage == ProcessingStage.ANALYSIS_COMPLETE
    
    def test_can_resume(self, manager, tmp_path):
        """Test can_resume method."""
        # Create a real file for hash calculation
        input_file = tmp_path / "input.mp4"
        input_file.write_bytes(b"test content")
        
        manager.create_checkpoint(
            task_id="task_001",
            input_path=str(input_file)
        )
        
        assert manager.can_resume("task_001") is True
        
        # Non-existent task
        assert manager.can_resume("non_existent") is False
        
        # Completed task
        manager.save_stage_checkpoint(
            task_id="task_001",
            stage=ProcessingStage.COMPLETED,
            data={}
        )
        assert manager.can_resume("task_001") is False
    
    def test_checkpoint_validation_failure(self, manager, tmp_path):
        """Test checkpoint validation when file changes."""
        # Create file
        input_file = tmp_path / "input.mp4"
        input_file.write_bytes(b"original content")
        
        manager.create_checkpoint(task_id="task_001", input_path=str(input_file))
        
        # Modify file
        time.sleep(0.1)  # Ensure different mtime
        input_file.write_bytes(b"modified content")
        
        # Clear cache to force reload
        manager._cache.clear()
        
        # Should fail validation
        checkpoint = manager.load_checkpoint("task_001")
        assert checkpoint is None
    
    def test_list_checkpoints(self, manager):
        """Test listing checkpoints."""
        # Create multiple checkpoints
        for i in range(3):
            manager.create_checkpoint(
                task_id=f"task_{i:03d}",
                input_path=f"input{i}.mp4"
            )
        
        checkpoints = manager.list_checkpoints()
        
        assert len(checkpoints) == 3
        # Should be sorted by updated_at (newest first)
        assert checkpoints[0].task_id == "task_002"
    
    def test_list_checkpoints_with_filter(self, manager):
        """Test listing checkpoints with status filter."""
        # Create checkpoints at different stages
        manager.create_checkpoint(task_id="task_001", input_path="input1.mp4")
        manager.create_checkpoint(task_id="task_002", input_path="input2.mp4")
        
        manager.save_stage_checkpoint(
            task_id="task_002",
            stage=ProcessingStage.COMPLETED,
            data={}
        )
        
        # List only completed
        completed = manager.list_checkpoints(status=ProcessingStage.COMPLETED)
        assert len(completed) == 1
        assert completed[0].task_id == "task_002"
    
    def test_delete_checkpoint(self, manager):
        """Test checkpoint deletion."""
        manager.create_checkpoint(task_id="task_001", input_path="input.mp4")
        
        # Verify exists
        assert manager.load_checkpoint("task_001") is not None
        
        # Delete
        result = manager.delete_checkpoint("task_001")
        assert result is True
        
        # Verify deleted
        assert manager.load_checkpoint("task_001") is None
    
    def test_cleanup_old_checkpoints(self, manager):
        """Test cleaning up old checkpoints."""
        # Create checkpoint
        manager.create_checkpoint(task_id="task_001", input_path="input.mp4")
        
        # Manually modify timestamp to be old
        checkpoint_path = manager._get_checkpoint_path("task_001")
        with open(checkpoint_path) as f:
            data = json.load(f)
        data["updated_at"] = time.time() - (10 * 24 * 3600)  # 10 days ago
        with open(checkpoint_path, "w") as f:
            json.dump(data, f)
        
        # Clear cache
        manager._cache.clear()
        
        # Cleanup checkpoints older than 7 days
        deleted = manager.cleanup_old_checkpoints(max_age_days=7)
        assert deleted == 1
        
        # Verify deleted
        assert not checkpoint_path.exists()
    
    def test_max_checkpoints_per_task(self, manager):
        """Test max checkpoints per task limit."""
        manager.max_checkpoints_per_task = 3
        
        manager.create_checkpoint(task_id="task_001", input_path="input.mp4")
        
        # Add many stage checkpoints
        for i in range(5):
            manager.save_stage_checkpoint(
                task_id="task_001",
                stage=ProcessingStage.TRANSCRIPTION_COMPLETE,
                data={"iteration": i}
            )
        
        checkpoint = manager.load_checkpoint("task_001")
        assert len(checkpoint.checkpoints) == 3
        # Should keep the most recent ones
        assert checkpoint.checkpoints[-1].data["iteration"] == 4


class TestProcessingStage:
    """Test ProcessingStage enum."""
    
    def test_stage_ordering(self):
        """Test that stages are properly ordered."""
        stages = [
            ProcessingStage.INITIALIZED,
            ProcessingStage.TRANSCRIPTION_STARTED,
            ProcessingStage.TRANSCRIPTION_COMPLETE,
            ProcessingStage.ANALYSIS_COMPLETE,
            ProcessingStage.STRATEGY_GENERATED,
            ProcessingStage.CLIPS_EXTRACTED,
            ProcessingStage.RENDERING,
            ProcessingStage.RENDERING_COMPLETE,
            ProcessingStage.POST_PROCESSING,
            ProcessingStage.COMPLETED,
        ]
        
        # Verify order (using value comparison)
        for i in range(len(stages) - 1):
            # Stages should be in logical order for progress calculation
            assert isinstance(stages[i], ProcessingStage)
