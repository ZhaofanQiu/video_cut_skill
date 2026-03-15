"""Interactive video editor for speech/talk videos."""

from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from video_cut_skill.models.semantic import VideoSemantics, ContentSegment, SegmentType
from video_cut_skill.models.session import EditSession, EditStrategy, UserFeedback, SessionState, EditIntent
from video_cut_skill.models.agent import AgentResponse, AgentAction, AgentActionType
from video_cut_skill.clients.aliyun_client import AliyunClient
from video_cut_skill.core.session_manager import SessionManager
from video_cut_skill.core.cache import MultiLevelCache
from video_cut_skill.core.cost_guardian import CostGuardian
from video_cut_skill.config import get_config, Config
from video_cut_skill.exceptions import VideoCutSkillError, SessionNotFoundError


def generate_id() -> str:
    """Generate unique ID."""
    import uuid
    return uuid.uuid4().hex[:12]


def get_video_duration(video_path: str) -> float:
    """Get video duration using FFmpeg.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds
    """
    try:
        from video_cut_skill.core.ffmpeg_wrapper import FFmpegWrapper
        wrapper = FFmpegWrapper()
        info = wrapper.get_video_info(video_path)
        return info.get("duration", 0.0)
    except Exception:
        # Fallback: return 0
        return 0.0


def extract_audio(video_path: str, output_path: Optional[str] = None) -> str:
    """Extract audio from video.

    Args:
        video_path: Path to video file
        output_path: Optional output path

    Returns:
        Path to extracted audio file (PCM WAV format for transcription)

    Raises:
        VideoCutSkillError: If audio extraction fails
    """
    import subprocess

    if not output_path:
        output_path = str(Path(video_path).with_suffix(".wav"))

    try:
        # Use FFmpeg directly with PCM format for transcription compatibility
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise VideoCutSkillError(f"Failed to extract audio: {e.stderr}") from e
    except Exception as e:
        raise VideoCutSkillError(f"Failed to extract audio: {e}") from e


class InteractiveEditor:
    """Interactive video editor for agent/conversational users.

    This is the main interface for interactive video editing, supporting:
    - Video analysis and transcription
    - Natural language editing commands
    - Multi-round iteration with feedback
    - Cost control and caching
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize interactive editor.

        Args:
            config: Optional configuration override
        """
        self.config = config or get_config()

        # Initialize components
        self.aliyun_client = AliyunClient(self.config.model.api_key)
        self.session_manager = SessionManager()
        self.cache = MultiLevelCache()
        self.cost_guardian = CostGuardian()

    def analyze(self, video_path: str) -> AgentResponse:
        """Analyze video and create editing session.

        This is the first step in the interactive editing workflow.
        It transcribes the video and prepares semantic analysis.

        Args:
            video_path: Path to video file

        Returns:
            AgentResponse with session info or confirmation request
        """
        # Get video duration
        duration = get_video_duration(video_path)

        # Cost check
        cost_check = self.cost_guardian.check_analyze(video_path, duration)

        if cost_check.requires_confirmation:
            # Create session but mark as awaiting confirmation
            session_id = self.session_manager.create_session(video_path)
            self.session_manager.update_session(
                session_id,
                state=SessionState.CREATED,
            )

            return AgentResponse(
                state="awaiting_confirm",
                message=cost_check.warning_message,
                data={
                    "session_id": session_id,
                    "video_path": video_path,
                    "duration": duration,
                    "estimated_cost": cost_check.estimated_cost,
                },
                available_actions=[
                    AgentAction(AgentActionType.CONFIRM, "确认分析"),
                    AgentAction(AgentActionType.CANCEL, "取消"),
                ],
                cost_info={"estimated_yuan": cost_check.estimated_cost},
            )

        # Proceed with analysis
        return self._do_analyze(video_path, duration)

    def _do_analyze(self, video_path: str, duration: float) -> AgentResponse:
        """Perform actual video analysis."""
        # Create session
        session_id = self.session_manager.create_session(video_path)

        # Check cache
        video_hash = self.session_manager.get_session(session_id).video_hash
        cached_semantics = self.cache.get_semantics(video_hash)

        if cached_semantics:
            self.session_manager.update_session(
                session_id,
                semantics=cached_semantics,
                state=SessionState.READY,
            )
            return self._create_ready_response(session_id, cached_semantics)

        # Start transcription
        self.session_manager.update_session(
            session_id,
            state=SessionState.TRANSCRIBING,
        )

        try:
            # Check if input is already an audio URL
            if video_path.startswith(("http://", "https://")) and \
               any(video_path.endswith(ext) for ext in ['.wav', '.mp3', '.m4a', '.mp4', '.ogg']):
                # Direct transcribe from URL
                audio_url = video_path
            else:
                # Extract audio from local video file
                audio_url = extract_audio(video_path)

            # Transcribe with configured model
            transcribe_kwargs = {
                'language_hints': self.config.model.language_hints,
            }
            
            # Add model selection if specified in config
            if hasattr(self.config.model, 'transcribe_model') and self.config.model.transcribe_model:
                transcribe_kwargs['model'] = self.config.model.transcribe_model
                print(f"   使用ASR模型: {self.config.model.transcribe_model}")
            
            # Add context hint if specified (for Qwen3-ASR-Flash)
            if hasattr(self.config.model, 'transcribe_context') and self.config.model.transcribe_context:
                transcribe_kwargs['context'] = self.config.model.transcribe_context
                print(f"   使用上下文提示: {self.config.model.transcribe_context[:50]}...")
            
            transcription = self.aliyun_client.transcribe(
                audio_url,
                **transcribe_kwargs,
            )

            # Build semantics
            self.session_manager.update_session(
                session_id,
                state=SessionState.ANALYZING,
            )

            semantics = self._build_semantics(video_path, transcription)

            # Cache results
            self.cache.set_semantics(video_hash, semantics)

            # Update session
            self.session_manager.update_session(
                session_id,
                semantics=semantics,
                state=SessionState.READY,
            )

            return self._create_ready_response(session_id, semantics)

        except Exception as e:
            self.session_manager.update_session(
                session_id,
                state=SessionState.ERROR,
                error_message=str(e),
            )
            return AgentResponse.error("分析视频时发生错误", str(e))

    def _build_semantics(
        self,
        video_path: str,
        transcription: Any,
    ) -> VideoSemantics:
        """Build semantic representation from transcription."""
        from video_cut_skill.models.semantic import VideoSemantics

        # Aggregate sentences into segments
        segments = self._aggregate_sentences(transcription.sentences)

        # Generate summaries (batch processing for cost efficiency)
        segments = self._generate_summaries(segments)

        # Extract topics and keywords
        all_topics = list(set(
            topic for seg in segments for topic in seg.topics
        ))
        all_keywords = list(set(
            kw for seg in segments for kw in seg.keywords
        ))

        return VideoSemantics(
            video_path=video_path,
            video_hash="",  # Will be set by caller
            duration=transcription.duration_ms / 1000,
            segments=segments,
            transcription=transcription,
            all_topics=all_topics,
            all_keywords=all_keywords,
        )

    def _aggregate_sentences(self, sentences: List[Any]) -> List[ContentSegment]:
        """Aggregate sentences into semantic segments."""
        if not sentences:
            return []

        config = get_config()
        min_duration = config.editing.min_segment_duration
        max_duration = config.editing.max_segment_duration
        pause_threshold = config.editing.pause_boundary_threshold

        segments = []
        current_sentences = []
        current_start = sentences[0].begin_time / 1000

        for i, sent in enumerate(sentences):
            current_sentences.append(sent)
            current_end = sent.end_time / 1000
            current_duration = current_end - current_start

            # Check if we should create a segment
            should_split = False

            # Split if max duration reached
            if current_duration >= max_duration:
                should_split = True

            # Split if long pause to next sentence
            if i < len(sentences) - 1:
                next_start = sentences[i + 1].begin_time / 1000
                pause = next_start - current_end
                if pause >= pause_threshold and current_duration >= min_duration:
                    should_split = True

            # Split on last sentence
            if i == len(sentences) - 1:
                should_split = True

            if should_split and current_sentences:
                # Create segment
                text = " ".join(s.text for s in current_sentences)
                segment = ContentSegment(
                    segment_id=f"seg_{len(segments)}",
                    start_time=current_start,
                    end_time=current_end,
                    duration=current_duration,
                    text=text,
                    segment_type=SegmentType.SPEECH,
                    speaker_id=current_sentences[0].speaker_id,
                )
                segments.append(segment)

                # Reset
                if i < len(sentences) - 1:
                    current_sentences = []
                    current_start = sentences[i + 1].begin_time / 1000

        return segments

    def _generate_summaries(self, segments: List[ContentSegment]) -> List[ContentSegment]:
        """Generate summaries for segments using LLM (batch processing)."""
        if not segments:
            return segments

        # Process each segment with LLM for high-quality summary
        for seg in segments:
            if seg.text:
                try:
                    # Generate summary using LLM
                    seg.summary = self._summarize_with_llm(seg.text)
                    # Extract keywords using LLM
                    seg.keywords = self._extract_keywords_with_llm(seg.text)
                    # Infer topics
                    seg.topics = self._infer_topics(seg.text, seg.summary)
                except Exception as e:
                    # Fallback to simple truncation on error
                    seg.summary = seg.text[:100] + "..." if len(seg.text) > 100 else seg.text
                    seg.keywords = [w for w in seg.text.split() if len(w) > 2][:5]

        return segments

    def _summarize_with_llm(self, text: str, max_chars: int = 100) -> str:
        """Generate one-sentence summary using LLM."""
        prompt = f"""请为以下文本生成一句话摘要（不超过{max_chars}字）：

{text}

摘要（一句话）："""

        response = self.aliyun_client.chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
        )
        
        # Clean up the response
        summary = response.strip()
        if len(summary) > max_chars:
            summary = summary[:max_chars-3] + "..."
        return summary

    def _extract_keywords_with_llm(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract keywords using LLM."""
        prompt = f"""请从以下文本中提取{max_keywords}个关键词，用逗号分隔：

{text}

关键词："""

        response = self.aliyun_client.chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=50,
        )
        
        # Parse keywords from response
        keywords = [kw.strip() for kw in response.split(",") if kw.strip()]
        return keywords[:max_keywords]

    def _infer_topics(self, text: str, summary: str) -> List[str]:
        """Infer topics from text and summary."""
        # Simple topic inference based on keywords
        topics = []
        
        # Common topic patterns for speech content
        topic_patterns = {
            "技术": ["技术", "开发", "代码", "软件", "系统", "算法", "AI", "人工智能"],
            "商业": ["商业", "市场", "产品", "用户", "客户", "销售", "营收", "盈利"],
            "创业": ["创业", "公司", "团队", "融资", "投资", "创始人", " startup"],
            "教育": ["教育", "学习", "课程", "学生", "老师", "知识", "培训"],
            "生活": ["生活", "日常", "健康", "饮食", "运动", "旅行", "家庭"],
            "观点": ["观点", "看法", "认为", "觉得", "建议", "推荐"],
        }
        
        content = text + " " + summary
        for topic, keywords in topic_patterns.items():
            if any(kw in content for kw in keywords):
                topics.append(topic)
        
        return topics if topics else ["未分类"]

    def _create_ready_response(
        self,
        session_id: str,
        semantics: VideoSemantics,
    ) -> AgentResponse:
        """Create response when video is ready for editing."""
        # Update session hash reference
        session = self.session_manager.get_session(session_id)
        if session and semantics:
            semantics.video_hash = session.video_hash

        segments_preview = [
            {"id": s.segment_id, "summary": s.summary or s.text[:50] if s.text else ""}
            for s in semantics.segments[:5]
        ]

        response = AgentResponse.ready_for_edit(
            segment_count=len(semantics.segments),
            duration=semantics.duration,
            topics=semantics.all_topics,
            segments_preview=segments_preview,
        )
        
        # Add session_id to data for subsequent operations
        response.data["session_id"] = session_id
        
        return response

    def edit(self, session_id: str, instruction: str, llm_model: str = "qwen3.5-plus") -> AgentResponse:
        """Process editing instruction.

        Args:
            session_id: Session identifier
            instruction: Natural language editing instruction
            llm_model: LLM model to use (qwen3.5-plus or qwen3.5-flash)

        Returns:
            AgentResponse with strategy or confirmation request
        """
        try:
            session = self.session_manager.get_session_or_raise(session_id)
        except SessionNotFoundError:
            return AgentResponse.error("会话不存在或已过期")

        if not session.semantics:
            return AgentResponse.error("视频尚未完成分析，请先调用analyze")

        # Parse intent
        context = session.get_context_for_llm()
        intent_data = self.aliyun_client.parse_edit_intent(instruction, context)
        intent = EditIntent(**intent_data, llm_model=llm_model)

        # Generate strategy
        strategy = self._generate_strategy(session.semantics, intent)

        # Cost check
        cost = 0.0  # Strategy generation cost already incurred
        cost_check = self.cost_guardian.check_edit(
            strategy.to_dict(),
            len(strategy.keep_segments),
        )

        # Always save strategy to session for tracking
        session.add_strategy(strategy)

        if cost_check.requires_confirmation:
            return AgentResponse.awaiting_confirmation(
                strategy_description=strategy.description,
                target_duration=strategy.target_duration,
                keep_count=len(strategy.keep_segments),
                cost=cost,
            )

        return self._execute_strategy(session_id, strategy)

    def _generate_strategy(
        self,
        semantics: VideoSemantics,
        intent: EditIntent,
    ) -> EditStrategy:
        """Generate editing strategy using LLM to select precise time ranges."""
        
        # 构建句子级数据给LLM
        sentences_data = []
        if semantics.transcription and semantics.transcription.sentences:
            for i, sent in enumerate(semantics.transcription.sentences):
                sentences_data.append({
                    "id": f"sent_{i}",
                    "start": sent.begin_time / 1000.0,
                    "end": sent.end_time / 1000.0,
                    "text": sent.text,
                })
        else:
            # 回退到段落数据
            for seg in semantics.segments:
                sentences_data.append({
                    "id": seg.segment_id,
                    "start": seg.start_time,
                    "end": seg.end_time,
                    "text": seg.text or seg.summary or "",
                })
        
        # 使用LLM选择时间范围（支持模型切换）
        llm_model = getattr(intent, 'llm_model', 'qwen3.5-plus')
        time_ranges = self._select_time_ranges_with_llm(
            user_intent=intent.description or "保留全部内容",
            sentences=sentences_data,
            target_duration=intent.target_duration,
            max_sentences=1024,  # 默认1024句
            llm_model=llm_model,
        )
        
        # 如果LLM返回空，使用所有段落
        if not time_ranges:
            time_ranges = [
                {"start": seg.start_time, "end": seg.end_time}
                for seg in semantics.segments
            ]
        
        # 计算总时长
        total_duration = sum(r["end"] - r["start"] for r in time_ranges)
        
        # 生成描述
        description = f"保留{len(time_ranges)}个片段"
        if intent.target_duration:
            description += f"，目标时长{intent.target_duration}秒，实际约{total_duration:.1f}秒"
        else:
            description += f"，总时长约{total_duration:.1f}秒"

        return EditStrategy(
            strategy_id=generate_id(),
            description=description,
            keep_segments=[],  # 不再使用段落ID模式
            time_ranges=time_ranges,  # 使用精确时间范围
            remove_fillers=True,
            optimize_pauses=True,
            target_duration=intent.target_duration,
        )
    
    def _select_time_ranges_with_llm(
        self,
        user_intent: str,
        sentences: List[Dict[str, Any]],
        target_duration: Optional[float] = None,
        max_sentences: int = 1024,
        llm_model: str = "qwen3.5-plus",
    ) -> List[Dict[str, float]]:
        """Use LLM to select precise time ranges based on user intent.
        
        Args:
            user_intent: User's natural language instruction
            sentences: List of sentences with id, start, end, text
            target_duration: Optional target duration in seconds
            max_sentences: Maximum number of sentences to include in prompt (default: 1024)
            llm_model: LLM model to use (qwen3.5-plus or qwen3.5-flash)
            
        Returns:
            List of time ranges [{"start": float, "end": float}, ...]
        """
        # 限制句子数量避免超出token限制，但默认给足1024个
        total_sentences = len(sentences)
        if total_sentences > max_sentences:
            # 智能截断：保留开头、中间采样、保留结尾
            head_count = max_sentences // 3
            tail_count = max_sentences // 3
            middle_count = max_sentences - head_count - tail_count
            
            head = sentences[:head_count]
            tail = sentences[-tail_count:]
            middle_start = head_count
            middle_end = total_sentences - tail_count
            step = max(1, (middle_end - middle_start) // middle_count)
            middle = sentences[middle_start:middle_end:step][:middle_count]
            
            sentences_subset = head + middle + tail
            truncation_note = f"\n[注：视频共{total_sentences}句话，此处展示{max_sentences}句代表性内容]"
        else:
            sentences_subset = sentences
            truncation_note = ""
        
        sentences_text = "\n".join([
            f"[{sent['id']}] {sent['start']:.1f}s - {sent['end']:.1f}s: {sent['text'][:150]}"
            for sent in sentences_subset
        ])
        
        duration_hint = ""
        if target_duration:
            min_duration = int(target_duration * 0.67)
            max_duration = int(target_duration * 1.33)
            duration_hint = f"""\n\n【时长要求】目标时长约 {target_duration} 秒（可接受范围：{min_duration}-{max_duration} 秒，即约 ±33% 偏差）。
重要提示：
1. 优先确保选中内容的完整性和语义连贯性，不要为了凑时长而截断句子
2. 宁可多包含一点内容，也不要让最后一句话被截断
3. 计算公式：总时长 = Σ(结束时间 - 开始时间)"""
        
        prompt = f"""你是一位专业的视频剪辑助手。你的任务是根据用户的剪辑需求，从视频语音转录内容中选择并排序要保留的片段。

【任务背景】
1. 以下内容是视频的语音识别转录结果，逐字记录了视频中的每一句话
2. 每个条目格式为：[ID] 开始时间-结束时间: 转录文本
3. 开始时间和结束时间是该句话在视频中的精确时间戳（单位：秒）
4. 每句话都是独立的语音单元，你可以：
   - 选择完整的句子
   - 选择句子的一部分（调整开始/结束时间）
   - 跨时间选择多个片段
   - **重新排列片段顺序**（这不是直播，你可以自由排序以优化叙事逻辑）

【用户需求】
{user_intent}{duration_hint}{truncation_note}

【视频语音转录内容】
{sentences_text}

【选择要求】
1. 仔细阅读每句话的内容，理解视频的叙事逻辑和信息结构
2. 根据用户需求选择最相关、信息密度最高的片段
3. 考虑同音字、口语化表达（如"三平"可能是"小米"的语音识别误差）
4. **重要：你可以自由调整片段的先后顺序，以创建更流畅、更有逻辑的视频叙事**
5. 严格按时长要求控制总长度，避免过长或过短

【输出格式】
请输出纯JSON格式（不要包含markdown代码块标记）：
{{
    "clip_sequence": [
        {{
            "source_id": "sent_2",
            "start": 44.8, 
            "end": 56.3, 
            "reason": "选择理由",
            "position": 1
        }},
        {{
            "source_id": "sent_5",
            "start": 65.9, 
            "end": 70.2, 
            "reason": "选择理由",
            "position": 2
        }}
    ],
    "total_duration": 15.8,
    "reasoning": "整体选择策略和排序逻辑的简要说明"
}}

注意：
- clip_sequence 中的片段会按照数组顺序在最终视频中呈现（你可以自由排序）
- source_id 是原始句子的ID，用于参考
- 时间必须在视频时间范围内
- total_duration 必须是你计算的实际总时长（结束时间-开始时间的累加）
- 如果只有一段话，clip_sequence 也可以只有一个元素"""

        try:
            print(f"   [LLM调用] 发送请求... (模型: {llm_model}, thinking: enabled)")
            response = self.aliyun_client.chat_completion(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
                enable_thinking=True,
                model=llm_model,  # 支持模型切换
            )
            
            # 保存LLM输入输出到文件
            debug_data = {
                "timestamp": datetime.now().isoformat(),
                "user_intent": user_intent,
                "target_duration": target_duration,
                "sentences_count": len(sentences),
                "llm_model": llm_model,
                "prompt": prompt,
                "llm_response": response,
            }
            import json
            debug_path = "/root/.openclaw/workspace/llm_debug.json"
            with open(debug_path, "w", encoding="utf-8") as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)
            print(f"   [调试] LLM输入输出已保存到: {debug_path}")
            
            # Parse JSON response
            import json
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)
            
            # 支持新的 clip_sequence 格式
            if "clip_sequence" in result:
                time_ranges = []
                for clip in result["clip_sequence"]:
                    time_ranges.append({
                        "start": clip.get("start", 0),
                        "end": clip.get("end", 0),
                    })
            else:
                # 兼容旧的 time_ranges 格式
                time_ranges = result.get("time_ranges", [])
            
            print(f"   [LLM响应] 选择 {len(time_ranges)} 个时间范围")
            for i, r in enumerate(time_ranges, 1):
                print(f"      片段{i}: {r.get('start', 0):.1f}s - {r.get('end', 0):.1f}s")
            
            # Validate ranges
            valid_ranges = []
            for r in time_ranges:
                start = r.get("start", 0)
                end = r.get("end", 0)
                if end > start and end - start > 0.3:  # 至少0.3秒
                    valid_ranges.append({"start": start, "end": end})
            
            return valid_ranges
            
        except Exception as e:
            print(f"⚠️ LLM time range selection failed: {e}, using all segments")
            return []


    def confirm_edit(self, session_id: str) -> AgentResponse:
        """Confirm and execute editing.

        Args:
            session_id: Session identifier

        Returns:
            AgentResponse with result
        """
        try:
            session = self.session_manager.get_session_or_raise(session_id)
        except SessionNotFoundError:
            return AgentResponse.error("会话不存在或已过期")

        if not session.current_strategy:
            return AgentResponse.error("没有待执行的剪辑策略")

        return self._execute_strategy(session_id, session.current_strategy)

    def _execute_strategy(
        self,
        session_id: str,
        strategy: EditStrategy,
    ) -> AgentResponse:
        """Execute editing strategy using AutoEditor."""
        self.session_manager.update_session(
            session_id,
            state=SessionState.RENDERING,
        )

        try:
            session = self.session_manager.get_session(session_id)
            if not session or not session.semantics:
                return AgentResponse.error("会话数据不完整")

            # Import AutoEditor here to avoid circular imports
            from video_cut_skill.auto_editor import AutoEditor, EditConfig

            # Build output path
            input_path = Path(session.video_path)
            output_path = input_path.parent / f"{input_path.stem}_edited{input_path.suffix}"

            # Prepare clip data - 优先使用time_ranges（句子级），然后回退到keep_segments（段落级）
            time_ranges = None
            keep_segments_data = []
            
            if strategy.time_ranges:
                # 使用精确时间范围（句子级剪辑）
                time_ranges = strategy.time_ranges
                print(f"   使用精确时间范围: {len(time_ranges)} 个片段")
            elif strategy.keep_segments and session.semantics:
                # 回退到段落级剪辑
                for seg in session.semantics.segments:
                    if seg.segment_id in strategy.keep_segments:
                        keep_segments_data.append({
                            "segment_id": seg.segment_id,
                            "start_time": seg.start_time,
                            "end_time": seg.end_time,
                            "text": seg.text[:100] if seg.text else "",
                        })
                print(f"   使用段落级剪辑: {len(keep_segments_data)} 个片段")

            # Create AutoEditor instance
            editor = AutoEditor(analysis_mode="audio")

            # 准备转录结果（将阿里云转录格式转换为AutoEditor格式）
            transcription_for_editor = None
            if session.semantics and session.semantics.transcription:
                trans = session.semantics.transcription
                # 转换为AutoEditor期望的格式
                segments = []
                for sent in trans.sentences:
                    # 转换词级时间戳
                    words = []
                    for word in sent.words:
                        words.append({
                            "text": word.text,
                            "begin_time": word.begin_time,
                            "end_time": word.end_time,
                            "punctuation": word.punctuation,
                        })
                    
                    segments.append({
                        "start": sent.begin_time / 1000.0,
                        "end": sent.end_time / 1000.0,
                        "text": sent.text,
                        "words": words,  # 包含词级时间戳
                    })
                transcription_for_editor = {
                    "text": trans.full_text,
                    "segments": segments,
                    "language": "zh",
                    "model_used": "aliyun-paraformer",
                }
                print(f"   使用阿里云转录结果: {len(segments)} 个句子, {sum(len(s.get('words', [])) for s in segments)} 个词")

            # Convert strategy to EditConfig
            config = EditConfig(
                target_duration=strategy.target_duration,
                aspect_ratio="16:9",
                add_subtitles=strategy.add_subtitles,
                output_path=str(output_path),
                time_ranges=time_ranges,  # 优先使用精确时间范围
                keep_segments=keep_segments_data if keep_segments_data else None,
                transcription=transcription_for_editor,  # 传入阿里云转录结果
            )

            # Execute the edit
            result = editor.process_video(
                str(input_path),
                config,
            )

            if result.error:
                raise Exception(result.error)

            self.session_manager.update_session(
                session_id,
                state=SessionState.COMPLETED,
                output_path=str(result.output_path),
            )

            return AgentResponse.completed(
                output_path=str(result.output_path),
                output_duration=result.duration,
            )

        except Exception as e:
            self.session_manager.update_session(
                session_id,
                state=SessionState.ERROR,
                error_message=str(e),
            )
            return AgentResponse.error("剪辑执行失败", str(e))

    def feedback(self, session_id: str, feedback_text: str) -> AgentResponse:
        """Process user feedback for iteration.

        Args:
            session_id: Session identifier
            feedback_text: User feedback text

        Returns:
            AgentResponse with updated strategy
        """
        try:
            session = self.session_manager.get_session_or_raise(session_id)
        except SessionNotFoundError:
            return AgentResponse.error("会话不存在或已过期")

        # Record feedback
        feedback = UserFeedback(
            feedback_id=generate_id(),
            feedback_text=feedback_text,
        )
        session.add_feedback(feedback)

        # Treat feedback as new editing instruction
        return self.edit(session_id, feedback_text)

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session status.

        Args:
            session_id: Session identifier

        Returns:
            Session status dict or None
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "state": session.state.name,
            "video_path": session.video_path,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "strategy_count": len(session.strategy_history),
            "has_output": session.output_path is not None,
        }
