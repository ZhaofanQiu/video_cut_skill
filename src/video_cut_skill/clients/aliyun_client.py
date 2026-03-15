"""Aliyun DashScope unified client for transcription and LLM."""

import os
import json
from typing import Optional, List, Dict, Any
from http import HTTPStatus
from pathlib import Path

from video_cut_skill.exceptions import TranscriptionError, LLMError
from video_cut_skill.models.semantic import (
    TranscriptionResult,
    Sentence,
    WordTimestamp,
)


class AliyunClient:
    """Unified client for Aliyun DashScope (transcription + LLM).

    This client provides a unified interface for:
    - Speech recognition (Paraformer realtime - supports local files)
    - Speech recognition (Qwen3-ASR-Flash - higher accuracy)
    - Chat completion (Qwen series)

    Requires DASHSCOPE_API_KEY environment variable or api_key parameter.

    Example:
        client = AliyunClient()

        # Transcribe audio with Paraformer (local file supported!)
        result = client.transcribe("audio.wav")

        # Transcribe audio with Qwen3-ASR-Flash (higher accuracy)
        result = client.transcribe("audio.wav", model="qwen3-asr-flash-realtime")

        # Chat completion
        response = client.chat_completion([
            {"role": "user", "content": "Hello"}
        ])
    """

    DEFAULT_TRANSCRIBE_MODEL = "paraformer-realtime-v2"
    DEFAULT_LLM_MODEL = "qwen3.5-plus"
    
    # Supported ASR models
    ASR_MODELS = {
        "paraformer-realtime-v2": "Paraformer实时语音识别",
        "qwen3-asr-flash-realtime": "Qwen3-ASR-Flash实时版 (稳定版)",
        "qwen3-asr-flash-realtime-2026-02-10": "Qwen3-ASR-Flash实时版 (2026-02-10快照)",
        "qwen3-asr-flash-realtime-2025-10-27": "Qwen3-ASR-Flash实时版 (2025-10-27快照)",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Aliyun client.

        Args:
            api_key: DashScope API key. If not provided, reads from
                    DASHSCOPE_API_KEY environment variable.

        Raises:
            ValueError: If API key is not provided or found in environment.
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "阿里云API Key未配置。请设置环境变量 DASHSCOPE_API_KEY "
                "或在初始化时传入api_key参数。"
            )

        # Import dashscope here to avoid dependency issues
        try:
            import dashscope
            self._dashscope = dashscope
            self._dashscope.api_key = self.api_key
        except ImportError:
            raise ImportError(
                "使用阿里云功能需要安装dashscope：pip install dashscope"
            )

    def transcribe(
        self,
        audio_path: str,
        model: str = "paraformer-realtime-v2",
        language_hints: Optional[List[str]] = None,
        context: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio file using specified ASR model.

        Supports both Paraformer and Qwen3-ASR-Flash models.

        Args:
            audio_path: Path to audio file (local file supported)
            model: ASR model to use. Options:
                - "paraformer-realtime-v2": Paraformer (default, stable)
                - "qwen3-asr-flash-realtime": Qwen3-ASR-Flash (higher accuracy)
                - "qwen3-asr-flash-realtime-2026-02-10": Qwen3-ASR-Flash (latest snapshot)
                - "qwen3-asr-flash-realtime-2025-10-27": Qwen3-ASR-Flash (snapshot)
            language_hints: Optional language hints (e.g., ["zh", "en"])
            context: Optional context text for Qwen3-ASR-Flash to improve recognition
                     of specific terms (e.g., "小米汽车 雷军 造车"). 
                     Only works with Qwen3-ASR-Flash models.
            **kwargs: Additional parameters for transcription

        Returns:
            TranscriptionResult with detailed timestamps

        Raises:
            TranscriptionError: If transcription fails
        """
        # Route to appropriate transcription method based on model
        if model.startswith("qwen3-asr-flash"):
            return self._transcribe_qwen3_asr(
                audio_path, 
                model=model, 
                language_hints=language_hints,
                context=context,
                **kwargs
            )
        else:
            # Default to Paraformer
            return self._transcribe_paraformer(
                audio_path, 
                language_hints=language_hints,
                **kwargs
            )

    def _transcribe_paraformer(
        self,
        audio_path: str,
        language_hints: Optional[List[str]] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe using Paraformer realtime recognition."""
        from dashscope.audio.asr import Recognition
        from pathlib import Path
        import subprocess
        import tempfile

        path = Path(audio_path)
        if not path.exists():
            raise TranscriptionError(f"音频文件不存在：{audio_path}")

        # Check if input is video file - need to extract audio first
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
        file_ext = path.suffix.lower()
        
        audio_file = str(path)
        temp_audio = None
        
        if file_ext in video_extensions:
            # Extract audio from video to WAV format
            temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio_file = temp_audio.name
            temp_audio.close()
            
            try:
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(path),
                    '-vn',
                    '-acodec', 'pcm_s16le',
                    '-ar', '16000',
                    '-ac', '1',
                    audio_file
                ]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                if temp_audio:
                    os.unlink(temp_audio.name)
                raise TranscriptionError(f"提取音频失败：{e.stderr}") from e

        try:
            # Create Recognition instance according to Python SDK documentation
            # https://help.aliyun.com/zh/model-studio/paraformer-real-time-speech-recognition-python-sdk
            recognition = Recognition(
                model="paraformer-realtime-v2",
                format='wav',
                sample_rate=kwargs.get('sample_rate', 16000),
                language_hints=language_hints or ['zh', 'en'],
                callback=None,  # Non-streaming call doesn't need callback
            )

            # Call recognition with local file
            # The call() method returns RecognitionResult directly
            result = recognition.call(audio_file)

            if result.status_code != HTTPStatus.OK:
                raise TranscriptionError(
                    f"转录请求失败：{getattr(result, 'message', '未知错误')}"
                )

            # Parse the result
            return self._parse_recognition_result(result, str(path))

        except Exception as e:
            if isinstance(e, TranscriptionError):
                raise
            raise TranscriptionError(f"转录过程中发生错误：{e}") from e
        finally:
            # Clean up temp file if created
            if temp_audio and os.path.exists(temp_audio.name):
                os.unlink(temp_audio.name)

    def _transcribe_qwen3_asr(
        self,
        audio_path: str,
        model: str = "qwen3-asr-flash-realtime",
        language_hints: Optional[List[str]] = None,
        context: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe using Qwen3-ASR-Flash recognition via OmniRealtimeConversation.
        
        Qwen3-ASR-Flash uses WebSocket-based real-time API, different from Paraformer.
        Reference: https://help.aliyun.com/zh/model-studio/qwen-speech-recognition
        
        Args:
            audio_path: Path to audio/video file
            model: Qwen3-ASR-Flash model variant
            language_hints: Language hints (e.g., ['zh', 'en'])
            context: Optional context text to improve recognition of specific terms
            **kwargs: Additional parameters
            
        Returns:
            TranscriptionResult
        """
        from pathlib import Path
        import subprocess
        import tempfile
        import base64
        import time
        import threading
        from dashscope.audio.qwen_omni import OmniRealtimeConversation, OmniRealtimeCallback, MultiModality
        from dashscope.audio.qwen_omni.omni_realtime import TranscriptionParams

        path = Path(audio_path)
        if not path.exists():
            raise TranscriptionError(f"音频文件不存在：{audio_path}")

        # Convert video/audio to PCM format (required by Qwen3-ASR-Flash)
        temp_pcm = tempfile.NamedTemporaryFile(suffix='.pcm', delete=False)
        pcm_file = temp_pcm.name
        temp_pcm.close()
        
        try:
            # Convert to PCM 16kHz mono
            cmd = [
                'ffmpeg', '-y',
                '-i', str(path),
                '-vn',
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-f', 's16le',
                pcm_file
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            os.unlink(pcm_file)
            raise TranscriptionError(f"转换音频格式失败：{e.stderr}") from e

        # Collect transcription results
        transcripts = []
        sentences = []
        session_id = None
        
        class Qwen3ASRCallback(OmniRealtimeCallback):
            def __init__(self):
                self.conversation = None
                self.final_texts = []  # Collect all final transcripts
                self.current_stash = ""
                self.session_complete = threading.Event()
                self.speech_active = False
                
            def on_open(self):
                pass
                
            def on_close(self, code, msg):
                self.session_complete.set()
                
            def on_event(self, response):
                try:
                    event_type = response.get('type')
                    
                    if event_type == 'session.created':
                        pass
                        
                    elif event_type == 'conversation.item.input_audio_transcription.completed':
                        # Final transcription result for a speech segment
                        transcript = response.get('transcript', '')
                        if transcript:
                            self.final_texts.append(transcript)
                            
                    elif event_type == 'conversation.item.input_audio_transcription.text':
                        # Stash/intermediate result
                        stash = response.get('stash', '')
                        if stash:
                            self.current_stash = stash
                            
                    elif event_type == 'rate_limits.updated':
                        # Session processing complete
                        self.session_complete.set()
                        
                except Exception as e:
                    print(f"[Callback Error] {e}")
        
        callback = Qwen3ASRCallback()
        
        try:
            # Create conversation
            conversation = OmniRealtimeConversation(
                model=model,
                url='wss://dashscope.aliyuncs.com/api-ws/v1/realtime',
                callback=callback
            )
            callback.conversation = conversation
            
            # Connect
            conversation.connect()
            
            # Configure session
            transcription_params = TranscriptionParams(
                language='zh',
                sample_rate=16000,
                input_audio_format="pcm"
            )
            
            conversation.update_session(
                output_modalities=[MultiModality.TEXT],
                enable_input_audio_transcription=True,
                transcription_params=transcription_params
            )
            
            # Send audio in chunks
            chunk_size = 3200
            with open(pcm_file, 'rb') as f:
                while chunk := f.read(chunk_size):
                    audio_b64 = base64.b64encode(chunk).decode('ascii')
                    conversation.append_audio(audio_b64)
                    time.sleep(0.01)  # Small delay to avoid flooding
            
            # End session
            conversation.end_session()
            
            # Wait for final results (poll with timeout)
            max_wait = 60  # 60 seconds max
            waited = 0
            while waited < max_wait:
                if callback.session_complete.is_set():
                    break
                time.sleep(0.5)
                waited += 0.5
            
            if waited >= max_wait:
                print("[Warning] Session completion timeout")
            
            conversation.close()
            
            # Build result from all final transcripts
            full_text = ' '.join(callback.final_texts) if callback.final_texts else callback.current_stash
            
            if not full_text:
                raise TranscriptionError("未识别到语音内容")
            
            # Create sentences from final texts
            from video_cut_skill.models.semantic import Sentence
            sentences = []
            for text in callback.final_texts:
                sentences.append(Sentence(
                    text=text,
                    begin_time=0,  # Qwen3-ASR-Flash doesn't provide timestamps per sentence
                    end_time=0,
                    words=[],
                ))
            
            return TranscriptionResult(
                full_text=full_text,
                sentences=sentences,
                duration_ms=0,  # Would need to calculate from file
                audio_format='pcm',
                sample_rate=16000,
                channel_id=0,
            )
            
        except Exception as e:
            if isinstance(e, TranscriptionError):
                raise
            raise TranscriptionError(f"Qwen3-ASR-Flash 转录失败：{e}") from e
        finally:
            # Clean up
            if os.path.exists(pcm_file):
                os.unlink(pcm_file)
            try:
                conversation.close()
            except:
                pass

    def _parse_recognition_result(self, result, audio_path: str) -> TranscriptionResult:
        """Parse RecognitionResult into TranscriptionResult.
        
        According to Python SDK docs, result.get_sentence() returns a list of sentences:
        Each sentence has:
        - text: str
        - begin_time: int
        - end_time: int
        - words: list of word timestamps
        """
        from pathlib import Path

        path = Path(audio_path)
        
        # Get sentences from result - it's a list!
        sentences_data = result.get_sentence()
        if not sentences_data:
            raise TranscriptionError("未识别到语音内容")

        # Handle both list and single dict formats
        if isinstance(sentences_data, dict):
            sentences_data = [sentences_data]

        # Parse sentences
        sentences = []
        for sent_data in sentences_data:
            if isinstance(sent_data, dict):
                # Parse words if available
                words = []
                for word_data in sent_data.get('words', []):
                    if isinstance(word_data, dict):
                        words.append(WordTimestamp(
                            text=word_data.get('text', ''),
                            begin_time=word_data.get('begin_time', 0),
                            end_time=word_data.get('end_time', 0),
                            punctuation=word_data.get('punctuation', ''),
                        ))

                sentences.append(Sentence(
                    text=sent_data.get('text', ''),
                    begin_time=sent_data.get('begin_time', 0),
                    end_time=sent_data.get('end_time', 0),
                    words=words,
                    speaker_id=sent_data.get('speaker_id'),
                ))

        if not sentences:
            raise TranscriptionError("未识别到有效语音内容")

        # Build full text
        full_text = ' '.join(s.text for s in sentences)

        # Get duration from last sentence
        duration_ms = sentences[-1].end_time if sentences else 0

        return TranscriptionResult(
            full_text=full_text,
            sentences=sentences,
            duration_ms=duration_ms,
            audio_format=path.suffix.lower().lstrip('.') or 'wav',
            sample_rate=16000,
            channel_id=0,
        )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Call Qwen LLM for chat completion using OpenAI compatible API.

        Args:
            messages: List of message dicts with "role" and "content"
            model: Model name (default: qwen3.5-plus)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters (e.g., enable_thinking)

        Returns:
            Generated text response

        Raises:
            LLMError: If LLM call fails
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            
            # Build request parameters
            request_params = {
                "model": model or self.DEFAULT_LLM_MODEL,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            
            # Handle enable_thinking via extra_body
            if kwargs.get("enable_thinking"):
                request_params["extra_body"] = {"enable_thinking": True}
            
            response = client.chat.completions.create(**request_params)
            
            # Extract content from response
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                raise LLMError("LLM返回空响应")
                
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMError(f"LLM调用过程中发生错误：{e}") from e

    def summarize_segment(self, text: str, max_chars: int = 100) -> str:
        """Generate one-sentence summary for a text segment."""
        prompt = f"""请为以下文本生成一句话摘要（不超过{max_chars}字）：

{text}

摘要："""

        return self.chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
        )

    def optimize_subtitles(
        self,
        words: List[Dict[str, Any]],
        max_chars_per_line: int = 20,
        aspect_ratio: str = "16:9",
    ) -> List[Dict[str, Any]]:
        """使用LLM优化字幕断句。
        
        Args:
            words: 词列表，每个词包含 text, begin_time, end_time, punctuation
            max_chars_per_line: 每行最大字数
            aspect_ratio: 视频比例，"16:9" 或 "9:16"
            
        Returns:
            优化后的字幕条目列表，每个包含 text, start, end
        """
        # 构建词序列文本
        words_text = ""
        for w in words:
            text = w.get("text", "")
            punct = w.get("punctuation", "")
            begin = w.get("begin_time", 0)
            end = w.get("end_time", 0)
            words_text += f"{text}{punct}[{begin},{end}]"
        
        # 构建完整文本（用于LLM理解语义）
        full_text = "".join(f"{w.get('text', '')}{w.get('punctuation', '')}" for w in words)
        
        is_vertical = aspect_ratio == "9:16"
        
        prompt = f"""你是字幕排版专家。请根据词级时间戳，将以下文本优化断句为字幕。

【视频比例】{'竖屏(9:16)' if is_vertical else '横屏(16:9)'}
【每行字数限制】{max_chars_per_line}字
【完整文本】{full_text}

【词级时间戳】
{words_text}

【任务要求】
1. 每行字数不超过{max_chars_per_line}字
2. 必须在词语边界处断开（不能切断词）
3. 语义完整，避免"产品上市呢也"这种半截话
4. 标点符号尽量在行尾
5. 保持时间顺序

【输出格式】
请输出JSON格式（不要包含markdown代码块标记）：
{{
    "subtitles": [
        {{
            "text": "第一行字幕文本",
            "start": 0,
            "end": 2500
        }},
        {{
            "text": "第二行字幕文本",
            "start": 2500,
            "end": 5000
        }}
    ]
}}

注意：
- start/end 是毫秒时间戳
- 必须从第一个词开始，到最后一个词结束
- 确保所有词都被包含在字幕中
"""

        try:
            response = self.chat_completion(
                [{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000,
            )
            
            # 解析JSON响应
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
            subtitles = result.get("subtitles", [])
            
            # 根据LLM返回的文本，匹配原始词的时间戳
            optimized = []
            word_idx = 0
            all_words_text = "".join(w.get("text", "") + w.get("punctuation", "") for w in words)
            
            for sub in subtitles:
                text = sub.get("text", "").strip()
                if not text:
                    continue
                
                # 清理文本用于匹配
                clean_text = text.replace(" ", "")
                
                # 从当前位置开始匹配
                matched_words = []
                temp_idx = word_idx
                temp_text = ""
                
                while temp_idx < len(words):
                    w = words[temp_idx]
                    word_str = w.get("text", "") + w.get("punctuation", "")
                    temp_text += word_str
                    
                    # 检查是否已匹配足够
                    if clean_text in temp_text.replace(" ", ""):
                        matched_words.append(w)
                        temp_idx += 1
                        break
                    elif temp_text.replace(" ", "").startswith(clean_text):
                        # 已经超出所需文本，截断
                        matched_words.append(w)
                        temp_idx += 1
                        break
                    else:
                        matched_words.append(w)
                        temp_idx += 1
                
                if matched_words:
                    # 使用匹配到的词的时间戳
                    start_time = matched_words[0].get("begin_time", 0) / 1000.0
                    end_time = matched_words[-1].get("end_time", 0) / 1000.0
                    
                    # 构建实际文本（只包含匹配到的词）
                    actual_text = "".join(w.get("text", "") + w.get("punctuation", "") for w in matched_words)
                    
                    optimized.append({
                        "text": actual_text,
                        "start": start_time,
                        "end": end_time,
                    })
                    
                    word_idx = temp_idx
                
                # 如果已用完所有词，停止
                if word_idx >= len(words):
                    break
            
            return optimized
            
        except Exception as e:
            # LLM优化失败，返回原始词的简单合并
            print(f"   ⚠️ LLM字幕优化失败: {e}，使用原始分词")
            return self._fallback_subtitle_split(words, max_chars_per_line)
    
    def _fallback_subtitle_split(
        self,
        words: List[Dict[str, Any]],
        max_chars: int = 20,
    ) -> List[Dict[str, Any]]:
        """LLM失败时的回退方案：简单按字数合并。"""
        subtitles = []
        current_text = ""
        current_start = None
        current_end = None
        
        for word in words:
            text = word.get("text", "")
            punct = word.get("punctuation", "")
            begin = word.get("begin_time", 0)
            end = word.get("end_time", 0)
            
            if current_start is None:
                current_start = begin
            
            # 检查加入这个词后是否超限
            candidate = current_text + text + punct
            if len(candidate) > max_chars and current_text:
                # 保存当前行
                subtitles.append({
                    "text": current_text,
                    "start": current_start / 1000.0,
                    "end": current_end / 1000.0,
                })
                # 开始新行
                current_text = text + punct
                current_start = begin
                current_end = end
            else:
                current_text = candidate
                current_end = end
        
        # 添加最后一行
        if current_text:
            subtitles.append({
                "text": current_text,
                "start": current_start / 1000.0,
                "end": current_end / 1000.0,
            })
        
        return subtitles

    def parse_edit_intent(
        self,
        user_query: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse user editing intent into structured format."""
        system_prompt = """你是一位专业的口播视频剪辑助手。请将用户的自然语言指令解析为结构化的剪辑意图。

当前视频信息：
- 总时长：{duration}秒
- 段落数：{segment_count}

请分析用户的指令，提取以下信息：
1. intent_type: 意图类型 (SELECT-选择性保留 | REMOVE-删除特定内容 | ADJUST-调整时长 | ENHANCE-增强效果)
2. filter_conditions: 过滤条件列表，每个条件包含：
   - type: "keyword" (关键词匹配) 或 "topic" (主题匹配)
   - value: 具体的值（从用户指令中提取的关键词，不要包含整个句子）
3. target_duration: 目标时长（秒），如果用户指定了时长要求
4. style_preference: 风格偏好 (compact-精简 | smooth-流畅 | complete-完整)

重要：
- 关键词应该是具体的实体词，如"小米汽车"、"造车"、"技术"等
- 不要将整个用户指令作为关键词
- 如果用户说"保留关于XX的部分"，提取XX作为关键词

请输出JSON格式（不要包含markdown代码块标记）：
{{
    "intent_type": "SELECT|REMOVE|ADJUST|ENHANCE",
    "description": "意图的自然语言描述",
    "filter_conditions": [
        {{"type": "keyword", "value": "提取的关键词1"}},
        {{"type": "keyword", "value": "提取的关键词2"}}
    ],
    "target_duration": null或具体秒数,
    "style_preference": "compact|smooth|complete"
}}""".format(
            duration=context.get("duration", "未知"),
            segment_count=context.get("segment_count", 0),
        )

        response = self.chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"用户指令：{user_query}"},
            ],
            temperature=0.3,
            enable_thinking=True,  # 开启thinking模式以获得更好的意图理解
        )

        # Parse JSON response
        try:
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)
            
            # Validate filter_conditions
            if not result.get("filter_conditions"):
                # Fallback: extract keywords from query
                result["filter_conditions"] = self._extract_keywords_from_query(user_query)
            
            return result
        except json.JSONDecodeError:
            return {
                "intent_type": "SELECT",
                "description": user_query,
                "filter_conditions": self._extract_keywords_from_query(user_query),
                "target_duration": None,
                "style_preference": "smooth",
            }
    
    def _extract_keywords_from_query(self, query: str) -> List[Dict[str, str]]:
        """Extract keywords from user query using LLM."""
        prompt = f"""从以下视频剪辑指令中提取关键词（用于内容匹配）。
只返回关键词列表，用逗号分隔。

指令：{query}

关键词："""
        
        try:
            response = self.chat_completion(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=50,
            )
            
            keywords = [kw.strip() for kw in response.split(",") if kw.strip()]
            return [{"type": "keyword", "value": kw} for kw in keywords[:5]]  # 最多5个
        except Exception:
            # Ultimate fallback
            return [{"type": "keyword", "value": query}]
