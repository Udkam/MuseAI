# AI 回复延迟诊断指南

> 适用版本：Stage 8D Batch 2（2026-05-29 skip_generate 优化版）  
> 相关文件：`app/application/tour_chat_service.py`、`app/infra/langchain/agents.py`

---

## 1. 如何触发埋点日志

每次用户在 tour 页发送消息，后端都会在日志中输出一组 `[perf]` 行。只需要正常使用小程序，日志就会自动产生。

---

## 2. 日志格式

### 2.1 JSON 模式（生产/默认）

每条 `[perf]` 日志是一个独立 JSON 行，结构如下：

```json
{
  "timestamp": "2026-05-29T14:23:01.452+08:00",
  "level": "INFO",
  "message": "[perf] session_loaded  duration_ms=12ms  ok=True",
  "module": "tour_chat_service",
  "extra": {
    "trace_id": "a3f2c1d0-...",
    "session_id": "sess-xxx",
    "perf": true,
    "stage": "session_loaded",
    "duration_ms": 12,
    "ok": true
  }
}
```

关键字段：
| 字段 | 说明 |
|------|------|
| `extra.perf` | 固定为 `true`，用于 grep 过滤 |
| `extra.trace_id` | 一次请求的唯一 ID，贯穿所有阶段 |
| `extra.stage` | 阶段名称（见 §3） |
| `extra.duration_ms` | 该阶段耗时（毫秒） |
| `extra.ok` | `true` = 正常完成，`false` = 发生异常 |
| `extra.elapsed_ms` | 部分阶段（如 first_token）记录的是从请求开始的累计时间 |

### 2.2 文本模式（开发环境）

```
2026-05-29 14:23:01.452 | INFO | tour_chat_service:ask_stream_tour:142 - [perf] session_loaded  duration_ms=12ms  ok=True
```

---

## 3. 阶段说明与正常范围

一次完整请求会依次产生以下 `[perf]` 日志行（按时间顺序）：

| stage | 产生位置 | 含义 | 正常范围 | 异常信号 |
|-------|---------|------|---------|---------|
| `session_loaded` | tour_chat_service | 从 PostgreSQL 加载 tour session | < 50ms | > 200ms → DB 连接池满 |
| `style_parsed` | tour_chat_service | 构建 system prompt（本地计算） | < 5ms | — |
| `tts_config` | tour_chat_service | 解析 TTS 人格配置 | < 30ms | `ok=False` → TTS 配置异常 |
| `rewrite` | agents.py | 查询改写（可能含 LLM 调用） | 0ms（无历史）或 300–800ms | > 1000ms → query_rewriter 超时 |
| `retrieve` | agents.py | 向量检索 + BM25（含 embedding） | 500–2000ms | > 3000ms → ES 慢或 embedding 超时 |
| `merge` | agents.py | 层级 chunk 合并（含 ES 父 chunk 查询） | 50–300ms | > 500ms → ES 连接慢 |
| `rerank` | agents.py | 重排序（外部 API 调用） | 200–800ms | > 1500ms → rerank 服务慢 |
| `filter` | agents.py | 动态文档过滤（本地计算） | < 10ms | — |
| `evaluate` | agents.py | 检索质量评分（本地计算） | < 5ms | — |
| `transform` | agents.py | 查询转换（仅低质量检索时触发，含 LLM） | 0ms 或 300–800ms | 频繁触发 → 知识库覆盖不足 |
| `generate_node` | agents.py | tour chat 场景：**已跳过**（`skipped=True duration_ms=0ms`）；其他流程仍执行 LLM | 0ms（tour）/ 3000–30000ms（其他） | tour 场景若此处出现 duration_ms > 100ms，说明 skip_generate 未生效 |
| `rag_run_total` | agents.py | 以上所有节点的总耗时 | — | 等于各节点之和 |
| `rag_pipeline` | tour_chat_service | 与 rag_run_total 相同，从调用侧测量 | — | 应与 rag_run_total 接近 |
| `prompt_build` | tour_chat_service | 组装最终 LLM prompt（本地，含 prompt_gateway） | < 100ms | > 500ms → Redis/DB prompt 缓存慢 |
| `llm_stream_start` | tour_chat_service | 发出第二次 LLM 流式请求的瞬间 | — | 时间戳，无 duration |
| `llm_stream` | tour_chat_service | 第二次 LLM 流式生成的总耗时（用户实际看到的内容） | 3000–20000ms | > 30000ms → LLM 冷启动或超时 |
| `first_token` | tour_chat_service | 从发送请求到收到第一个 chunk 的时间（elapsed_ms） | 1500–5000ms | > 8000ms → LLM 极慢或阻塞 |
| `stream_done` | tour_chat_service | RAG + LLM 流式的总耗时（t_rag 到结束） | — | ≈ rag_pipeline + prompt_build + llm_stream |
| `total` | tour_chat_service | 整个函数从入口到 done 事件的总耗时 | — | 用户感受到的等待时间 |

---

## 4. 已修复：双重 LLM 调用（Stage 8D Batch 2）

**修复日期：2026-05-29**

### 修复前现象（已消除）

```
请求进入
  ├─ rag_agent.run()  ←── LLM 调用 #1（非流式，~18s，结果被丢弃）
  └─ llm_provider.generate_stream()  ←── LLM 调用 #2（流式，~15s）
  [perf] total  duration_ms=40000ms
```

### 修复后流程

```
请求进入
  ├─ rag_agent.run(skip_generate=True)
  │    └─ generate_node  [perf] generate_node  skipped=True  duration_ms=0ms
  │         ← 跳过 LLM 调用，保留检索上下文
  │
  └─ llm_provider.generate_stream()  ←── 唯一 LLM 调用（流式，~8-15s）
  [perf] total  duration_ms=~15000ms  ← 节省约 15-25s
```

### 修复方案

- `RAGState` 新增 `skip_generate: bool` 字段
- `RAGAgent.generate()` 在 `skip_generate=True` 时立即返回，不调用 LLM
- `RAGAgent.run()` 新增 `skip_generate: bool = False` 参数（默认 False，其他调用方不受影响）
- `tour_chat_service._stream_rag()` 调用 `rag_agent.run(..., skip_generate=True)`

### 修复后 perf 日志特征

```
[perf] rewrite           duration_ms=0ms    ok=True
[perf] retrieve          duration_ms=1800ms ok=True
[perf] merge             duration_ms=120ms  ok=True
[perf] rerank            duration_ms=450ms  ok=True
[perf] filter            duration_ms=2ms    ok=True
[perf] evaluate          duration_ms=1ms    ok=True
[perf] generate_node     skipped=True       duration_ms=0ms   ← 不再有 LLM 调用
[perf] rag_run_total     duration_ms=2400ms ok=True           ← 节省 ~18s
[perf] rag_pipeline      duration_ms=2410ms ok=True
[perf] prompt_build      duration_ms=8ms    ok=True
[perf] llm_stream_start
[perf] first_token       elapsed_ms=~3000ms                   ← 用户等待约 3 秒
[perf] llm_stream        duration_ms=~10000ms ok=True
[perf] total             duration_ms=~13000ms ok=True         ← 从 40s → 13s
```

### 验证方法

运行后查看：
- `generate_node` 是否出现 `skipped=True duration_ms=0ms`（说明修复生效）
- `rag_pipeline` 是否从 ~22s 缩短到 ~3s 以内
- `total` 是否从 ~40s 缩短到 ~15s 以内

---

## 5. 快速过滤日志的命令

### 5.1 查看某次请求的完整链路

```bash
# 先找到 trace_id（从前端 Console 或 done 事件的 trace_id 字段）
grep '"trace_id": "a3f2c1d0-xxxx"' logs/app.log | python3 -m json.tool

# 只看 perf 行
grep '"perf": true' logs/app.log | grep '"trace_id": "a3f2c1d0-xxxx"'
```

### 5.2 找出所有慢请求（total > 30s）

```bash
# JSON 模式
python3 -c "
import json, sys
for line in sys.stdin:
    try:
        r = json.loads(line)
        extra = r.get('extra', {})
        if extra.get('perf') and extra.get('stage') == 'total' and extra.get('duration_ms', 0) > 30000:
            print(f\"{r['timestamp']}  trace={extra['trace_id']}  total={extra['duration_ms']}ms\")
    except: pass
" < logs/app.log
```

### 5.3 统计各阶段平均耗时

```bash
python3 -c "
import json, sys, collections
stages = collections.defaultdict(list)
for line in sys.stdin:
    try:
        r = json.loads(line)
        extra = r.get('extra', {})
        if extra.get('perf') and 'duration_ms' in extra:
            stages[extra['stage']].append(extra['duration_ms'])
    except: pass
for stage, durations in sorted(stages.items()):
    avg = sum(durations) / len(durations)
    mx = max(durations)
    print(f'{stage:25s}  avg={avg:7.0f}ms  max={mx:7d}ms  n={len(durations)}')
" < logs/app.log
```

### 5.4 文本模式快速过滤

```bash
grep "\[perf\]" logs/app.log | grep "trace_id=a3f2c1d0"
```

---

## 6. 如何判断瓶颈

根据日志中各阶段的 `duration_ms`，对照以下决策树：

```
generate_node 是否 skipped=True？
├─ NO（duration_ms > 100ms）→ skip_generate 未生效，检查 tour_chat_service._stream_rag() 调用
│
total > 20s（skip_generate 已生效后）？
├─ YES → 看 retrieve duration_ms
│        ├─ > 3000ms → ES 慢或 embedding 超时（见 §7）
│        └─ < 3000ms → 看 llm_stream duration_ms：> 15s → LLM 冷启动或网络慢
│
total < 15s?
├─ 看 first_token elapsed_ms
│  ├─ > 5000ms → 用户等待第一个字太久
│  │   ├─ 看 rewrite duration_ms：> 500ms → 关闭 query_rewriter 先验证
│  │   ├─ 看 retrieve duration_ms：> 2000ms → ES 慢或 embedding 超时
│  │   └─ 看 rerank duration_ms：> 1000ms → rerank 服务慢
│  └─ < 3000ms → 体验尚可，看 llm_stream 是否太长
│
transform 出现？
└─ 表示检索质量低（< 0.7 分），会触发额外 LLM 调用
   → 考虑优化知识库内容或调低 score_threshold
```

---

## 7. 当前不在埋点范围的子阶段

以下子步骤在本次埋点中归入上层阶段，未单独拆分：

| 子步骤 | 归入阶段 | 如需单独测量 |
|--------|---------|-------------|
| embedding API 调用 | `retrieve` | 在 `infra/providers/embedding.py embed()` 加 timing |
| ES dense 查询 | `retrieve` | 在 `infra/elasticsearch/client.py search_dense()` 加 timing |
| ES BM25 查询 | `retrieve` | 在 `infra/elasticsearch/client.py search_bm25()` 加 timing |
| RRF 融合排序 | `retrieve` | 在 `domain/services/retrieval.py` 加 timing |
| TTS 句级流式 | `stream_done` 内 | 在 `application/tts_streaming.py` 加 timing |

如果 `retrieve` 阶段持续 > 2000ms，建议下一步在 `embedding.py` 和 `client.py` 各加一层计时以确定是 embedding 慢还是 ES 慢。

---

## 8. 检查清单

运行一次测试后，按以下顺序看日志：

- [ ] `session_loaded` < 50ms（DB 正常）
- [ ] `tts_config` ok=True（TTS 配置正常）
- [ ] `generate_node` 是否出现 `skipped=True duration_ms=0ms`（若出现 `duration_ms > 100ms`，说明 skip_generate 未生效）
- [ ] `retrieve` < 2000ms（ES + embedding 正常）
- [ ] `rerank` < 1000ms（rerank 服务正常）
- [ ] `transform` 是否出现（出现 = 检索质量不足）
- [ ] `first_token` elapsed_ms < 5000ms（用户感知延迟可接受）
- [ ] `total` < 20000ms（整体目标）
