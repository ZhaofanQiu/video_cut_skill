# 云端服务统一规划文档

## 设计原则
**单一服务商优先，减少用户账号负担**

---

## 推荐方案：阿里云全栈

| 功能 | 阿里云服务 | 优势 |
|------|-----------|------|
| **语音识别** | 阿里云智能语音交互 | 中文优化好，价格低 |
| **大模型文本** | 阿里云百炼/通义千问 | 中文场景强 |
| **高光提取** | 通义千问 + 自研算法 | 语义理解 + 时间戳对齐 |
| **画面理解** | 阿里云视觉智能 | 视频分析、场景检测 |

**备选方案：腾讯云**
- 如果用户已有腾讯云账号，可平替

**不推荐：多服务商混合**
- ❌ OpenAI + 阿里云 + AWS（账号太多）

---

## 功能映射

### 阶段1：本地优先（当前）
```
语音识别 → Whisper tiny/base (本地)
文本理解 → 关键词匹配 (本地)
高光提取 → 关键词密度 (本地)
画面理解 → scenedetect (本地)
```

### 阶段2：云端增强（未来）
```
语音识别 → 阿里云语音识别 (云端)
文本理解 → 通义千问 (云端)
高光提取 → 通义千问语义分析 (云端)
画面理解 → 阿里云视觉智能 (云端)
```

---

## 接口设计

### 统一云端客户端
```python
class CloudServiceClient:
    """统一云端服务客户端"""
    
    def __init__(self, provider: str = "aliyun", api_key: str = None):
        self.provider = provider
        self.api_key = api_key
    
    def transcribe(self, audio_path: str) -> TranscriptResult:
        """语音识别"""
        if self.provider == "aliyun":
            return self._aliyun_transcribe(audio_path)
        elif self.provider == "tencent":
            return self._tencent_transcribe(audio_path)
    
    def analyze_text(self, text: str, prompt: str) -> str:
        """大模型文本理解"""
        # 使用通义千问/混元
        pass
    
    def analyze_video_frames(self, video_path: str) -> List[FrameAnalysis]:
        """画面理解"""
        # 使用阿里云视觉智能
        pass
```

---

## 用户配置简化

```yaml
# config.yaml - 仅需一个API Key
cloud:
  provider: aliyun  # 或 tencent
  api_key: sk-xxx   # 仅需这一个
  
  # 功能开关
  features:
    transcribe: true      # 云端语音识别
    text_analysis: true   # 大模型理解
    video_analysis: true  # 画面理解
```

---

## 成本估算（阿里云）

| 功能 | 单价 | 7分钟视频成本 |
|------|------|--------------|
| 语音识别 | ￥0.006/秒 | ￥2.5 |
| 大模型调用 | ￥0.006/千token | ￥0.1 |
| 画面分析 | ￥0.1/分钟 | ￥0.7 |
| **总计** | - | **￥3.3/视频** |

---

## 实施计划

### 当前（本地）
- ✅ 智能转录模块（tiny/base）
- ✅ 静音检测
- ✅ 动态模型选择

### 阶段1：云端语音识别
- 集成阿里云语音识别 API
- 保留本地 fallback

### 阶段2：大模型理解
- 集成通义千问
- 实现语义高光提取

### 阶段3：画面理解
- 集成阿里云视觉智能
- 多模态融合

---

## 代码预留

所有云端功能通过统一接口调用：
```python
if config.cloud.enabled:
    result = cloud_client.transcribe(video)
else:
    result = local_transcriber.transcribe(video)
```

---

## 生产环境优化规划

### 任务队列与并发控制

**目标：** 限制并发转录任务数，避免内存不足

**设计：**
```python
class TaskQueue:
    """视频处理任务队列"""
    
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.queue = []
        self.running = []
    
    async def submit(self, task: VideoTask) -> TaskResult:
        """提交任务到队列"""
        if len(self.running) >= self.max_concurrent:
            self.queue.append(task)
            await self._wait_for_slot()
        
        self.running.append(task)
        try:
            return await self._process(task)
        finally:
            self.running.remove(task)
            self._process_next()
```

**配置：**
```yaml
# config.yaml
queue:
  max_concurrent: 2        # 最大并发数
  max_queue_size: 10       # 队列最大长度
  timeout_seconds: 3600    # 任务超时时间
  retry_count: 2           # 失败重试次数
```

**实施阶段：**
- 阶段1：本地任务队列（内存/Redis）
- 阶段2：分布式队列（RabbitMQ/Celery）

---

## 完整实施路线图

| 阶段 | 功能 | 优先级 | 预计时间 |
|------|------|--------|----------|
| 当前 | 本地转录（tiny/base） | ✅ 完成 | - |
| 当前 | 静音检测 | ✅ 完成 | - |
| 当前 | 分级转录策略 | ✅ 完成 | - |
| P1 | **任务队列（max_concurrent=2）** | ⭐⭐⭐ 高 | 1-2天 |
| P1 | 临时文件自动清理 | ⭐⭐ 中 | 0.5天 |
| P2 | 阿里云语音识别 | ⭐⭐⭐ 高 | 2-3天 |
| P2 | 错误日志系统 | ⭐⭐ 中 | 1天 |
| P3 | 通义千问文本理解 | ⭐⭐ 中 | 3-5天 |
| P4 | 阿里云视觉智能 | ⭐ 低 | 5-7天 |
| P5 | 分布式队列 | ⭐ 低 | 3-5天 |
