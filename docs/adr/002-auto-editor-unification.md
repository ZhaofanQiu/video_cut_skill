# ADR-002: AutoEditor Unification

## Status
Accepted

## Context
The project had two separate AutoEditor implementations:
1. `auto_editor.py` - Phase 1 basic implementation with scene detection
2. `auto_editor_enhanced.py` - Phase 2+ implementation with SmartTranscriber

This created confusion:
- Users didn't know which one to use
- Duplicate code between implementations
- Inconsistent APIs
- Maintenance burden of keeping both in sync

## Decision
Merge both implementations into a single `AutoEditor` class with a mode flag.

### Unified API

```python
class AutoEditor:
    def __init__(self, use_smart_transcriber: bool = True, ...):
        """
        Args:
            use_smart_transcriber: 
                True  -> Smart mode (dynamic model selection, audio detection)
                False -> Basic mode (scene detection, fixed models)
        """
```

### Mode Capabilities

| Feature | Smart Mode | Basic Mode |
|---------|------------|------------|
| Dynamic model selection | ✅ | ❌ |
| Audio stream detection | ✅ | ❌ |
| Scene detection | ❌ | ✅ |
| `cut_by_scenes()` | ❌ | ✅ |
| `process_video()` | ✅ | ✅ |
| `extract_highlights()` | ✅ | ✅ |

## Implementation Details

### Type Safety
```python
class AutoEditor:
    transcriber: Optional[Union[Transcriber, SmartTranscriber]]
    _smart_transcriber: Optional[SmartTranscriber]
    scene_detector: Optional[SceneDetector]
```

### Runtime Checks
```python
def cut_by_scenes(self, ...):
    if self.use_smart_transcriber:
        raise RuntimeError("cut_by_scenes only available in basic mode")
    if self.scene_detector is None:
        raise RuntimeError("Scene detector not initialized")
    # ... implementation
```

## Consequences

### Positive
- Single, clear entry point for users
- Reduced code duplication
- Easier maintenance
- Clear migration path from basic to smart mode

### Negative
- More complex initialization logic
- Some runtime errors only caught at execution (mode mismatch)
- Larger class with conditionals

## Migration Guide

### From auto_editor.py (Basic Mode)
```python
# Before
from video_cut_skill.auto_editor import AutoEditor
editor = AutoEditor()

# After (unchanged for basic mode)
from video_cut_skill.auto_editor import AutoEditor
editor = AutoEditor(use_smart_transcriber=False)
```

### From auto_editor_enhanced.py (Smart Mode)
```python
# Before
from video_cut_skill.auto_editor_enhanced import AutoEditor, EditConfig

# After
from video_cut_skill.auto_editor import AutoEditor, EditConfig
editor = AutoEditor(use_smart_transcriber=True)  # or just AutoEditor()
```

## Related Decisions
- ADR-001: Tiered Transcription Architecture
- ADR-003: Future Cloud Integration

## References
- [Refactoring: Improving the Design of Existing Code](https://martinfowler.com/books/refactoring.html)
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)
