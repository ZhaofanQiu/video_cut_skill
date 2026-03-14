# ADR-001: Tiered Transcription Architecture

## Status
Accepted

## Context
The video processing pipeline needs to handle both quick analysis of long videos and high-quality transcription of output clips. Different use cases have different requirements:

1. **Full video analysis** (for finding highlights): Speed is priority, accuracy can be lower
2. **Output clip transcription** (for final videos): Quality is priority, speed is less critical
3. **Resource constraints**: Local environment has limited memory (4GB), can't run large models

## Decision
Implement a tiered transcription architecture with three tiers:

### Tier 1: Fast Analysis (TINY model)
- **Use case**: Initial scan of long videos (>3 minutes)
- **Model**: whisper-tiny (~39M parameters)
- **Speed**: ~10x realtime
- **Accuracy**: Good enough for keyword detection
- **Memory**: ~1GB

### Tier 2: Standard Quality (BASE model)
- **Use case**: Short videos (<3 minutes) or output clips
- **Model**: whisper-base (~74M parameters)
- **Speed**: ~7x realtime
- **Accuracy**: Balanced quality for most use cases
- **Memory**: ~1GB

### Tier 3: Cloud API (Future)
- **Use case**: Professional-quality output when accuracy is critical
- **Models**: whisper-small/medium/large via API
- **Speed**: Depends on API
- **Accuracy**: High to professional
- **Memory**: Minimal local requirements

## Implementation

```python
class SmartTranscriber:
    def select_model(self, video_path: str, is_output: bool = False) -> ModelSize:
        duration = self.get_video_duration(video_path)
        
        if is_output:
            # Output videos use highest local quality
            return ModelSize.BASE
        else:
            # Analysis mode uses speed/quality tradeoff
            if duration > 180:  # > 3 minutes
                return ModelSize.TINY
            else:
                return ModelSize.BASE
```

## Consequences

### Positive
- Optimal resource usage based on task requirements
- Fast iteration during development and testing
- Foundation for future cloud integration
- Clear upgrade path as hardware improves

### Negative
- Two different models to maintain
- Potential inconsistency between analysis and output quality
- Users may be confused about which tier is being used

## Alternatives Considered

### Single Model (BASE only)
- **Rejected**: Too slow for long video analysis
- **Impact**: Would make batch processing impractical

### Always Use Largest Model
- **Rejected**: Memory constraints prevent running large models locally
- **Impact**: Would require immediate cloud implementation, delaying release

### User-Specified Model Only
- **Rejected**: Requires technical knowledge from users
- **Impact**: Poor user experience for non-technical users

## Related Decisions
- ADR-002: AutoEditor Unification (merging smart and basic modes)
- ADR-003: Cloud Service Architecture (future)

## References
- [Whisper Model Card](https://github.com/openai/whisper/blob/main/model-card.md)
- [Whisper Performance Benchmarks](https://github.com/openai/whisper/discussions/63)
