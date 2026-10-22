# 诊小通 Agent — 项目说明文档

| 项目 | 内容 |
|---|---|
| 产品名称 | 诊小通 Agent |
| 系统版本 | v2.1.0 |
| 项目类型 | 互联网医院智能服务平台（企业级医疗 AI 应用） |
| 代码位置 | `zhenxiao/backend`（后端）、`zhenxiao/web`（前端） |

---

## 一、项目概述

### 1.1 产品定位

诊小通 Agent 定位于 **"从症状输入到挂号建议的完整医疗服务闭环"**，面向互联网医院、线上健康咨询、医疗服务与医疗大模型应用开发学习场景。

系统围绕「**分诊、问诊、用药、报告、记录、挂号**」六类高频医疗服务流程构建业务闭环，采用前后端分离架构，把多 Agent 协作、RAG 知识库、联网增强、会话记忆、报告解读和预约挂号整合在一个系统中。

### 1.2 技术栈

| 层次 | 选型 |
|---|---|
| 前端 | Vue 3.5 + Vite 6 + Element Plus + Pinia + Vue Router |
| 后端 | FastAPI + SQLAlchemy 2 + Pydantic v2 |
| Agent 编排 | LangGraph（StateGraph 条件边 + 并行 fan-out） |
| 模型调用 | OpenAI 兼容协议（`langchain-openai`，base_url/api_key 可配置） |
| 联网检索 | Tavily（DeepResearch，可选） |
| 数据库 | MySQL（默认）或 SQLite（未配置 MySQL 时自动回落） |
| 知识库 | 本地 Markdown 13 篇，字符 n-gram TF-IDF + 余弦相似度检索（无外部依赖） |
| 前端运行端口 | **5178**（规格书 4.1 / AC-2） |
| 后端运行端口 | **8012** |

### 1.3 核心特性

- **多 Agent 协作**：7 个专职 Agent（路由/上下文/检索/联网/推理/格式化/安全）由 LangGraph 编排，前端可视化展示每一步 `AgentTrace`。
- **无 Key 也能用**：未配置大模型时自动降级为"本地规则 + RAG 知识库摘要"，仍给出"先解答、后建议"的科普回答（规格书 2.4 硬约束）。
- **医疗合规硬约束**：不得确诊、不得开处方、不得给具体剂量、不得绝对化表达；所有回答自动追加免责声明。
- **可追溯**：每次回答返回结构化字段 + 证据列表（本地知识库/联网来源）+ 量化指标 + 完整链路轨迹。

---

## 二、系统架构

### 2.1 分层结构

```
┌──────────────────────────────────────────────────────────────┐
│  前端工作台  Vue3 + Element Plus          127.0.0.1:5178      │
│  左侧固定导航 + 欢迎区 + 统计卡片 + 功能面板 + 结果/链路/证据面板  │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP/JSON（开发环境经 Vite 代理 /api）
┌───────────────────────────▼──────────────────────────────────┐
│  接口层  route/  FastAPI                  127.0.0.1:8012      │
│  chat · scenes · sessions · records · encounters · profile     │
│  appointments · reports · settings · metrics · departments     │
└───────────────────────────┬──────────────────────────────────┘
┌───────────────────────────▼──────────────────────────────────┐
│  业务编排层  service/                                          │
│  chat_service（核心编排）· memory（会话记忆）· session_service   │
│  encounter_service · appointment_service · report_service      │
└───────────┬───────────────────────────────┬──────────────────┘
            │                               │
┌───────────▼───────────────┐   ┌───────────▼──────────────────┐
│  Agent 层  agent/         │   │  基础能力层  utils/           │
│  LangGraph 多 Agent 图     │   │  llm · prompts · rules        │
│  graph/router/context/rag │   │  rag_retriever · compliance   │
│  research/reasoning/      │   │  fallback · report_fallback   │
│  formatter/safety         │   │  json_tools · state           │
└───────────────────────────┘   └───────────┬──────────────────┘
                                            │
                          ┌─────────────────▼──────────────────┐
                          │  数据层  model/                     │
                          │  SQLAlchemy + MySQL/SQLite          │
                          │  sessions/messages/health_profiles/ │
                          │  encounters/appointments            │
                          └────────────────────────────────────┘
                          ┌────────────────────────────────────┐
                          │  知识库  data/knowledge_base/*.md   │
                          └────────────────────────────────────┘
```

### 2.2 多 Agent 推理链路（规格书 3.8 / C1）

```
                    ┌─────────────────────────────────────────┐
 START ──► RouterAgent ──► ContextAgent ──┬──► RAGAgent      │ 并发 fan-out
         场景路由         患者上下文+      │   本地知识库召回   │ （同一 superstep）
         triage/         历史对话+        │                   │
         consultation/   本地症状线索      └──► ResearchAgent  │
         medication                           联网 DeepResearch│
                    └───────────┬────────────────────────────┘
                                │ join（两者都完成）
                                ▼
                          ReasoningAgent          大模型结构化推理
                                │                 （JSON 解析）
                   ┌────────────┴────────────┐
              解析成功                    解析失败
                   │                        ▼
                   │                  FormatterAgent       非法 JSON 修复
                   │                        │             （条件触发）
                   │              ┌─────────┴─────────┐
                   │          修复成功            修复失败且
                   │              │              retries < 3
                   │              │                  │
                   │              │            ┌─────┘
                   │              │            ▼
                   │              │     回 ReasoningAgent（退避 0.8s×retries）
                   │              │
                   │              └────► SafetyAgent ◄────┐
                   │                   合规替换+科室收敛   │
                   ▼                   +免责声明          │
              SafetyAgent ─────────────────────────────► END
                                                          ▲
              LLM 未启用 / 重试超限 ──► FallbackAgent ──────┘
                                        规则+RAG 摘要兜底
```

各 Agent 职责：

| # | Agent | 职责 | 关键实现 |
|---|---|---|---|
| 1 | **RouterAgent** | 场景路由（triage/consultation/medication） | `utils/rules.suggest_scene()`；接口层可 `forced_scene` 强制指定 |
| 2 | **ContextAgent** | 整理患者信息、历史对话，产出本地症状线索（不得作为最终结论） | `rules.extract_clues()` + 高危信号标注 |
| 3 | **RAGAgent** | 召回本地知识库证据 | `utils/rag_retriever`，`top_k` 可配（默认 6） |
| 4 | **ResearchAgent** | 联网 DeepResearch 补充时效性证据 | Tavily；失败/未配置时返回**降级证据** |
| 5 | **ReasoningAgent** | 调用大模型完成结构化医学推理 | JSON 优先；LLM 未启用时置 `llm_skipped` 直接短路到兜底 |
| 6 | **FormatterAgent** | 输出非法 JSON 时结构化修复 | `json_tools.repair_json()`；最多重试 3 次，退避 `0.8s × retries` |
| 7 | **SafetyAgent** | 合规检查 + 科室收敛 + 追加免责声明 | `compliance_guard` + `rules.match_department` |
| 8 | **FallbackAgent** | 规则 + RAG 摘要兜底 | `utils/fallback`（见 3.3） |

**结构化输出失败时的降级顺序**（规格书 3.8）：`JSON 解析 → 叙事解析 → JSON 修复 → 叙事重试 → 规则兜底`。

---

## 三、功能模块说明

### M1 智能分诊台（FR-TRIAGE）

- **入口**：`POST /api/triage`；前端 `/triage`
- **输入**：`message`（症状主诉，必填）、`patient_context`（年龄/性别/既往病史/过敏史/用药史，可选）、`enable_deep_search`
- **处理**：RouterAgent 识别为分诊 → ContextAgent 整理上下文与本地线索 → RAG + 联网并发检索 → ReasoningAgent 结构化推理 → SafetyAgent 合规检查与科室收敛
- **输出**：`recommended_department`（**必须从系统科室列表选取，前端以醒目渐变卡片展示**）、`risk_level`、`answer`、`evidence`、`red_flags`、`follow_up_questions`、`health_advice`、`metrics`、`trace`、`disclaimer`
- **降级**：模型不可用/输出不可解析 → FallbackAgent（风险等级沿用本地评估），`thinking_steps` 标注降级

### M2 线上问诊（FR-CONSULT）

- **入口**：`POST /api/consultation`（通用入口 `POST /api/chat` 走同一链路）；前端 `/chat`
- **会话记忆**：未传 `session_id` 时生成 UUID 并落库（标题取首条消息前 30 字）；读取最近 **12** 条历史作为上下文，Prompt 中取最近 **4** 条
- **处理**：与分诊同一链路，场景为"线上问诊"
- **落库**：写入用户消息、助手回答，并落一条 `encounters` 记录
- **异常**：失败信息在前端以**助手气泡**呈现

### M3 用药咨询（FR-MEDICATION）

- **入口**：`POST /api/medication`；前端 `/medication`
- **处理**：SystemPrompt 切换为药学角色；**推荐科室固定归一化为「药学门诊」**（任何路径，包括降级）；检索查询词偏重"用药安全/药物相互作用/禁忌/特殊人群"
- **硬约束**：不得给出具体处方剂量
- **前端**：顶部渐变"建议咨询科室：药学门诊"横幅

### M4 问诊记录（FR-RECORD）

- **入口**：`GET /api/records?user_id&days`（另保留 `GET /api/encounters`）
- **参数**：`days` 取 1~365，默认 7（前端提供 7/30/180 天切换）
- **处理**：读取 `encounters` 表，按创建时间倒序
- **前端**：场景统计卡片 + 记录卡片列表 + 弹窗展示完整摘要；支持按场景筛选

### M5 报告查询与 AI 解读（FR-REPORT）

- **入口**：`GET /api/reports`、`GET /api/reports/{report_id}/interpret`
- **内置数据**：每个用户 3 份模拟报告（血常规 / 胸部 CT / 肝肾功能），每份报告自带所属科室（血液科 / 呼吸科 / 肾内科）与检查日期
- **解读**：大模型启用时调用模型给出科普解释与就医建议，否则用 `report_fallback` 规则兜底；返回文本经 `compliance_guard` 处理
- **风险定级**：`items[].flag != "正常"` 即异常；有异常判为中风险，否则低风险
- **输出**：`{id, department, risk_level, analysis, interpretation}`

### M6 预约挂号（FR-APPOINTMENT）

- **入口**：
  - `GET /api/departments` — 科室列表（附录 A 的 15 个科室）
  - `GET /api/appointments/schedule?department=呼吸科&user_id=` — 未来 7 天上午/下午排班号源
  - `POST /api/appointments` — 创建预约
  - `GET /api/appointments?user_id=` — 我的预约
  - `DELETE /api/appointments/{id}` — 取消预约
- **排班生成**：`random.Random(科室名)` 作随机种子 → **同科室结果稳定可复现**；未来 7 天 × 上午/下午，每天 2 个半天，每个半天 5 个时间段，每时段总号源 `quota = 6`，剩余 `remaining = 总数 − 已预约数`
- **业务规则**：剩余号源由已预约记录实时扣减；`remaining <= 0` 时返回 **400「当前号源已约满」**；相同（科室+医生+日期+时段）的"已预约"记录去重，**重复提交返回既有 ID（幂等，仅对同一用户生效）**；取消仅对 `status='已预约'` 的记录生效
- **预约号**：`id` 展示为 `YL + 6 位数字`（如 `YL000021`）

### M7 系统设置与数据管理（FR-SETTINGS）

- **入口**：`GET /api/settings`、`DELETE /api/sessions`
- **状态展示**：大模型状态（`llm_enabled = Key 非空 且 base_url 非空 且 模型名非空`）、API 地址、模型名、联网检索状态、`rag_top_k`、知识库规模
- **安全**：页面**不展示 API Key 明文**，仅展示是否已配置
- **一键清空**：删除 `sessions`、`messages`、`encounters`、`appointments` 四张表全部数据（前端二次确认）

---

## 四、接口清单

Base URL：`http://127.0.0.1:8012`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/chat` | 通用问诊（走 consultation 场景，由 RouterAgent 判定） |
| POST | `/api/triage` | 智能分诊（强制 triage 场景） |
| POST | `/api/consultation` | 线上问诊（强制 consultation 场景） |
| POST | `/api/medication` | 用药咨询（强制 medication 场景） |
| GET | `/api/sessions` | 会话列表（含消息数、最后一条消息、更新时间） |
| GET | `/api/sessions/{session_id}/messages` | 会话消息（最多 100 条） |
| DELETE | `/api/sessions/{session_id}` | 删除指定会话（级联删消息与记录） |
| DELETE | `/api/sessions` | **清空全部数据**（四张表） |
| GET | `/api/records` | 问诊记录（`user_id`、`days` 1~365、`scene`） |
| GET | `/api/encounters` | 问诊记录（兼容入口，参数同上） |
| GET | `/api/profile/{user_id}` | 健康档案 |
| PUT | `/api/profile/{user_id}` | 保存健康档案 |
| GET | `/api/reports` | 报告列表 |
| GET | `/api/reports/{report_id}/interpret` | 报告 AI 解读 |
| GET | `/api/departments` | 科室列表（15 个） |
| GET | `/api/appointments/schedule` | 科室排班（`department`、`user_id`） |
| POST | `/api/appointments` | 创建预约 |
| GET | `/api/appointments` | 我的预约 |
| DELETE | `/api/appointments/{appointment_id}` | 取消预约 |
| GET | `/api/metrics` | 平台指标 |
| GET | `/api/settings` | 系统设置状态 |

交互式文档：`http://127.0.0.1:8012/docs`

### 核心响应结构（ChatResponse）

| 字段 | 中文名称 | 含义 |
|---|---|---|
| `session_id` | 会话 ID | 未传时生成的 UUID |
| `scene` | 场景 | `triage` / `consultation` / `medication` |
| `recommended_department` | 建议归某部门 | 已收敛到系统科室列表 |
| `risk_level` | 风险等级 | `low` / `medium` / `high` |
| `answer` | 最终答复 | 面向用户的精炼、合规回答 |
| `evidence` | 证据依据 | 最多 8 条，每条含 `source/title/score/content` |
| `red_flags` | 红旗信号 | 提示需立即线下就医的高危症状 |
| `follow_up_questions` | 建议追问 | 引导补充关键信息 |
| `health_advice` | 健康建议 | 生活方式与观察建议 |
| `metrics` | 指标 | `mode`（llm/fallback）、`evidence_count`、`retries`、`answer_source` 等 |
| `trace` | Agent 轨迹 | `AgentTrace(agent, action, detail, duration_ms)` |
| `thinking_steps` | 推理步骤 | 对内可读的推理说明（不直接展示给用户） |
| `disclaimer` | 免责声明 | 合规提示文本 |

---

## 五、数据模型

### 5.1 ER 关系

```
sessions 1───n messages          （会话与消息）
sessions 1───n encounters        （会话与问诊记录）
health_profiles（按 user_id 独立）
appointments（按 user_id 独立）
```

### 5.2 表结构

**sessions（会话）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | String(36) PK | 会话 ID（UUID） |
| `title` | String(120) | 标题（取首条消息前 30 字） |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

**messages（消息）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BigInteger PK | 自增 |
| `session_id` | String(36) | 会话 ID（索引） |
| `role` | String(16) | `user` / `assistant` |
| `content` | Text | 内容 |
| `metadata` | Text | JSON（场景、风险、科室、trace 等） |
| `created_at` | DateTime | 时间 |

**health_profiles（健康档案）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `user_id` | String(64) PK | 用户 ID |
| `age` / `gender` | Integer / String(8) | 年龄 / 性别 |
| `chronic_diseases` / `allergy_history` / `medication_history` | String(512) | 慢性病 / 过敏史 / 用药史 |
| `updated_at` | DateTime | 更新时间 |

**encounters（问诊记录）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BigInteger PK | 自增 |
| `session_id` / `user_id` | String | 会话 / 用户 |
| `scene` | String(32) | `triage` / `consultation` / `medication`（三类统一落库） |
| `chief_complaint` | Text | 主诉 |
| `risk_level` | String(16) | 风险等级 |
| `department` | String(64) | 推荐科室 |
| `summary` | Text | 回答摘要 |
| `metadata` | Text | JSON |
| `created_at` | DateTime | 时间 |

**appointments（预约）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BigInteger PK | 自增（展示为 `YL` + 6 位） |
| `user_id` / `department` / `doctor` / `doctor_title` | String | 预约信息 |
| `visit_date` | Date | 就诊日期 |
| `period` | String(8) | `上午` / `下午` |
| `time_slot` | String(32) | 时间段 |
| `status` | String(16) | `已预约` / `已取消` |
| `created_at` | DateTime | 时间 |

### 5.3 数据规模约束（规格书 6.3）

| 项 | 约束 | 实现位置 |
|---|---|---|
| 会话消息读取上限 | 接口按 100 条 | `utils/rules.HISTORY_API_LIMIT` |
| 上下文记忆 | 推理取最近 12 条，Prompt 取最近 4 条 | `HISTORY_LIMIT` / `prompts.history_texts(limit=4)` |
| 证据上限 | 返回最多 8 条 | `rules.MAX_EVIDENCE`，SafetyAgent 与出口双重截断 |
| 记录查询天数 | 1~365，默认 7 | `encounter_service.normalize_days` |

---

## 六、核心机制详解

### 6.1 本地知识库检索（FR-RAG）

- **载入**：`data/knowledge_base/*.md`，按 `##` 二级标题切块（当前 13 篇 → 49 个知识块）
- **打分**：字符 2-gram 的 **TF-IDF + 余弦相似度**，纯 Python 实现，无向量数据库、无外部依赖
- **返回**：`Evidence(source, title, score, content)`，`top_k` 由 `RAG_TOP_K` 配置（默认 6）
- **设计取舍**：规格书 2.3 提到 chroma/milvus，而 2.4/3.9 要求"轻量关键词倒排/余弦相似度"，本项目采用后者

### 6.2 降级模式：无 Key 也能给出有效回答

未配置大模型时，`ReasoningAgent` 置 `llm_skipped`，图条件边**直达 FallbackAgent**（不做无意义的 Reasoning↔Formatter 空转）。兜底回答结构：

```
① 结合本地知识库回答用户问题
   （把 RAG 证据按"人群匹配 → 相对分数分层 → 跨文档题名相关性校验 → 同文档补足"
     筛选后整理成最多 3 条要点，非医学结论，只做原文摘录与排序）
② 就医建议 / 用药边界 / 高危风险提示
③ 免责声明（compliance_guard 统一追加）
```

效果示例（同一批提问，降级模式下）：

| 提问 | 回答要点 |
|---|---|
| 最近总是失眠… | 失眠常见表现 + 需要警惕的情况 → 建议神经内科门诊评估 |
| 血压高平时要注意什么 | 血压监测：长期记录家庭血压… → 就医建议 |
| 布洛芬和感冒灵能一起吃吗 | 相互作用与重复用药风险 → 用药安全建议咨询药学门诊 |

### 6.3 医疗安全合规（FR-SAFETY）

`utils/compliance.py` 的 `compliance_guard()` 执行两项处理，覆盖三场景回答与报告解读：

| 替换前 | 替换后 |
|---|---|
| 确诊为 | 需要由医生评估是否为 |
| 一定是 | 可能为 |
| 必须服用 | 是否用药需要医生评估 |
| 剂量是 | 具体剂量需要遵医嘱 |

若文本中缺失免责声明，则追加标准文案：

> 以上内容仅用于健康科普和就医参考，不能替代医生诊断、处方或治疗。

### 6.4 科室收敛（规格书 3.1）

推荐科室必须落在附录 A 的 15 个科室内，采用**三重收敛**：

1. 三个场景的 SystemPrompt 注入科室清单，明确禁止自造科室名；
2. `rules.match_department()`：精确匹配 → 最长包含匹配（「呼吸内科」→「呼吸科」，且避免「内科」抢占更具体科室）；
3. 收敛优先级：`模型输出科室 > 回答文本中的科室 > 本地规则推测 > 默认「内科」`。

**附录 A 科室列表**：消化科、妇产科、皮肤科、内分泌科、神经内科、骨科、外科、内科、男科、生殖医学科、眼科、肾脏病中心、泌尿外科、呼吸科、药学门诊。

### 6.5 风险分级（附录 B）

| 等级 | 含义 | 行动建议 |
|---|---|---|
| 低风险 `low` | 未识别明确高危信号 | 健康观察 + 生活方式调整，症状加重应就医 |
| 中风险 `medium` | 含持续/需观察症状 | 记录变化，必要时门诊 |
| 高风险 `high` | 含高危红旗症状 | 立即线下就医/急诊/急救 |

红旗信号识别支持**口语同义词展开**（`utils/rules.expand()`）：胸口疼→胸痛、喘不上气→呼吸困难、发烧→发热、拉肚子→腹泻、睡不着→失眠、心慌→心悸 等，避免"胸口疼还喘不上气"被误判为低风险。

---

## 七、项目结构

```
zhenxiao/
├── README.md                     快速上手（安装/启动/常见问题）
├── backend/
│   ├── main.py                   应用入口与路由注册
│   ├── config.py                 环境变量与数据库 URL
│   ├── requirements.txt          后端依赖
│   ├── route/                    接口层
│   │   ├── chat.py               POST /api/chat
│   │   ├── scenes.py             POST /api/triage|consultation|medication
│   │   ├── _chat_helper.py       三场景共用调用逻辑
│   │   ├── sessions.py           /api/sessions*
│   │   ├── records.py            GET /api/records
│   │   ├── encounters.py         GET /api/encounters
│   │   ├── profile.py            /api/profile/{user_id}
│   │   ├── appointments.py       /api/appointments*
│   │   ├── reports.py            /api/reports*
│   │   ├── settings.py           GET /api/settings
│   │   ├── metrics.py            GET /api/metrics
│   │   ├── departments.py        GET /api/departments
│   │   └── schemas.py            Pydantic 请求/响应模型
│   ├── service/                  业务编排层
│   │   ├── chat_service.py       核心对话编排（读历史→跑图→落库→返回）
│   │   ├── memory.py             会话与消息读写
│   │   ├── session_service.py    会话列表/删除/一键清空
│   │   ├── encounter_service.py  记录查询（天数过滤）
│   │   ├── appointment_service.py排班生成/预约/取消/幂等
│   │   ├── report_service.py     报告列表与 AI 解读
│   │   └── profile_service.py    健康档案
│   ├── agent/                    LangGraph 多 Agent
│   │   ├── graph.py              图构建、条件边、并行 join、重试上限
│   │   ├── router.py             RouterAgent
│   │   ├── context.py            ContextAgent
│   │   ├── rag.py                RAGAgent
│   │   ├── research.py           ResearchAgent（联网 + 降级证据）
│   │   ├── reasoning.py          ReasoningAgent
│   │   ├── formatter.py          FormatterAgent
│   │   └── safety.py             SafetyAgent
│   ├── utils/                    基础能力层
│   │   ├── state.py              AgentState 状态契约 + initial_state
│   │   ├── llm.py                模型调用封装与启用判定
│   │   ├── prompts.py            三场景 SystemPrompt + 用户提示组装
│   │   ├── rules.py              科室清单/规则路由/红旗信号/规模常量
│   │   ├── rag_retriever.py      知识库切块与余弦检索
│   │   ├── compliance.py         合规替换与免责声明
│   │   ├── fallback.py           规则 + RAG 摘要兜底
│   │   ├── report_fallback.py    报告内置数据与规则解读
│   │   └── json_tools.py         JSON 解析与修复
│   ├── model/                    数据层
│   │   ├── database.py           引擎、会话工厂、get_db
│   │   ├── entities.py           五张表 ORM 定义
│   │   ├── .env                  本地环境变量（含真实 Key，勿提交）
│   │   └── .env.example          环境变量模板
│   └── data/knowledge_base/      13 篇本地 Markdown 知识库
└── web/
    ├── package.json
    ├── vite.config.js            端口 5178 + /api 代理到 8012
    ├── index.html
    └── src/
        ├── main.js               Vue 应用入口
        ├── App.vue               整体布局与左侧导航
        ├── api/index.js          接口封装
        ├── router/index.js       7 条路由
        ├── stores/               Pinia（会话 / 设置）
        ├── i18n/index.js         中英文案
        ├── style.css             主题变量（含暗色）
        └── views/                TriageView / ChatView / EncounterView /
                                  ReportView / AppointmentView / SettingsView /
                                  ProfileView
```

---

## 八、运行与部署

### 8.1 环境要求

| 项 | 要求 | 本项目验证环境 |
|---|---|---|
| 操作系统 | Windows 10/11（推荐）、Linux、macOS | Windows |
| 后端运行时 | Python 3.11+（推荐 3.11） | 3.10.21 验证可用 |
| 前端运行时 | Node.js 18+、npm 9+ | Node 18+ / npm 11 |
| 数据库 | MySQL 或 SQLite | MySQL 8（127.0.0.1:3306，库 `zhenxiao`） |

### 8.2 启动后端（127.0.0.1:8012）

```bash
cd zhenxiao/backend
pip install -r requirements.txt
# 环境变量：复制模板后按需填写（可全部留空，走降级模式）
copy model\.env.example model\.env
python -m uvicorn main:app --host 127.0.0.1 --port 8012
```

健康检查：`GET http://127.0.0.1:8012/api/health` → `{"status":"ok"}`

### 8.3 启动前端（127.0.0.1:5178）

```bash
cd zhenxiao/web
npm install
npm run dev          # 开发模式，/api 经 Vite 代理到 8012
npm run build        # 生产构建，产物在 dist/
```

打开 `http://127.0.0.1:5178` 即为工作台。

### 8.4 配置说明

配置来源优先级：**系统/用户环境变量 > `backend/model/.env`**。

| 系统环境变量 | 配置字段 | 说明 |
|---|---|---|
| `DASHSCOPE_API_KEY_2` | `dashscope_api_key_2` | 大模型 API Key（留空 = 降级模式） |
| `DASHSCOPE_BASE_URL` | `dashscope_base_url` | OpenAI 兼容端点 |
| `DASHSCOPE_CHAT_MODEL` | `dashscope_chat_model` | 模型名 |
| `TAVILY_API_KEY` | `tavily_api_key` | 联网检索 Key（可选） |
| `RAG_TOP_K` | `rag_top_k` | 检索条数，默认 6 |
| `DEEP_SEARCH_ENABLED` | `deep_search_enabled` | 联网检索总开关 |
| `DATABASE_URL` | `database_url` | 直接指定数据库连接串 |
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` | 同名 | MySQL 连接信息 |

**数据库回落规则**：`DATABASE_URL` 非空则用它；否则 `MYSQL_HOST` 非空则拼 MySQL 连接串；否则使用 SQLite（`backend/zhenxiao.db`），无需任何外部依赖。

### 8.5 常见问题

**Q1：明明配了 Key，为什么还是降级模式？**

Windows 环境变量**只在进程启动时读取一次**。设完系统/用户环境变量后，已打开的终端、IDE、Python 进程不会自动获得，必须**完全关闭并重新打开**（PyCharm 需重启 IDE）。

```powershell
# ① 进程能否看到（为空 = 没继承到）
$env:DASHSCOPE_API_KEY_2
# ② 应用配置是否读到
python -c "from config import settings; from utils import llm; print(len(settings.dashscope_api_key_2), llm.is_enabled())"
# ③ 运行中的服务实际状态
curl http://127.0.0.1:8012/api/settings     # 期望 llm_enabled: true
```

强制让当前会话立刻拿到系统变量：

```powershell
$env:DASHSCOPE_API_KEY_2 = [Environment]::GetEnvironmentVariable('DASHSCOPE_API_KEY_2','Machine')
python -m uvicorn main:app --host 127.0.0.1 --port 8012
```

**Q2：`vite build` 报 `EPERM: remove ...esbuild-xxx`？**
esbuild 在 Windows 上删除临时目录失败的宿主机问题（与项目代码无关）。换普通终端重试或 `npm cache clean --force`；开发用 `npm run dev` 不受影响。

**Q3：前端 5178 打不开？**
确认后端已在 8012 运行（代理目标），以及 5178 未被占用（`vite.config.js` 设置了 `strictPort`，端口被占用会直接报错而不是自动换端口）。

**Q4：不想要 MySQL？**
把 `model/.env` 里的 `MYSQL_HOST` 和 `DATABASE_URL` 都留空，系统自动使用 SQLite 文件库，五张表启动时自动创建。

**Q5：参考依据里出现"联网检索暂不可用"？**
这是 ResearchAgent 的降级占位证据（规格书 3.10 要求的行为），说明本次未取到真实联网结果。排查入口在 `GET /api/settings`：

| 字段 | 含义 |
|---|---|
| `deep_search_enabled` | 配置开关（`DEEP_SEARCH_ENABLED`） |
| `deep_search_key_configured` | Tavily Key 是否配置 |
| `deep_search_available` | **实际可用性**（综合开关 + Key + 依赖包判断） |
| `deep_search_issue` | 不可用原因（空串 = 可用），例如"缺少 Python 依赖 tavily-python（…），请执行：pip install tavily-python" |

最常见原因是**当前解释器未安装 `tavily-python`**：不同 Python 环境（如 `miniconda3` base 与项目 `.venv`）的包互不共享，IDE 选中的解释器必须自己装依赖。链路 `trace` 中 `ResearchAgent.detail` 也会写明具体原因。

---

## 九、测试与验收

### 9.1 验证方式

开发阶段使用过三个临时测试脚本（接口自测、降级回答质量检查、端到端验收），**交付前已按"只保留最终代码"的要求删除**。后续如需回归，可按以下方式验证。

**接口可交互验证**：打开 `http://127.0.0.1:8012/docs`（Swagger UI），直接对 22 个端点发请求。

**关键路径人工核对清单**：

| 顺序 | 操作 | 预期 |
|---|---|---|
| 1 | `GET /api/health` | `{"status":"ok"}` |
| 2 | `GET /api/departments` | 返回 15 个科室，含"药学门诊" |
| 3 | `POST /api/triage` 传"发热两天、咳嗽有黄痰、体温38.7℃" | `recommended_department=呼吸科`、`risk_level` 为枚举值、`evidence` 非空、`trace` ≥ 4 步 |
| 4 | `POST /api/medication` 传"布洛芬和感冒灵能一起吃吗" | `recommended_department=药学门诊`、回答含免责声明、无处方剂量 |
| 5 | `GET /api/appointments/schedule?department=呼吸科` | 7 天 × 上下午，含 `remaining` |
| 6 | 同参数 `POST /api/appointments` 两次 | 第一次 `created=true`，第二次 `created=false` 且返回同一 `appointment_id`（幂等） |
| 7 | `DELETE /api/appointments/{id}` 两次 | 第一次 `status=已取消`，第二次 `400` |
| 8 | `GET /api/records?days=7` / `30` / `180` | 均返回 `records` 列表，`days` 回显正确 |
| 9 | `GET /api/settings` | 含 `llm_enabled`、`base_url`、`rag_top_k`，且**不含 API Key 明文** |
| 10 | 清空 `DASHSCOPE_API_KEY_2` 后重启 | `/api/settings` 显示 `llm_enabled:false`，提问仍返回 `metrics.mode=fallback` 的科普回答 |

**边界核对**：非法科室、超出 7 天的日期、满号时段均应返回 `400`；不存在的会话应返回 `404`。

### 9.2 验收标准（规格书第 7 章）实测结果

交付前的实测结果如下（当时使用上述临时脚本执行）：

| 编号 | 验收项 | 通过标准 | 结果 |
|---|---|---|---|
| AC-1 | 后端启动 | `GET /api/health` 返回 `{"status":"ok"}` | ✅ |
| AC-2 | 前端启动 | `http://127.0.0.1:5178` 正常打开工作台 | ✅ |
| AC-3 | 分诊闭环 | 输入"发热两天、咳嗽有黄痰、体温38.7℃"能返回推荐科室、风险等级、证据与 Agent 链路 | ✅ 科室=呼吸科、风险=medium、证据 8 条、链路 6 步 |
| AC-4 | 问诊记忆 | 同一会话内追问可结合上文作答 | ✅ |
| AC-5 | 用药咨询 | 询问"布洛芬和感冒灵能一起吃吗"返回用药安全参考且无处方剂量 | ✅ 科室=药学门诊 |
| AC-6 | 报告解读 | 选择报告可返回异常指标科普解释与就医建议 | ✅ 3 份报告 |
| AC-7 | 预约挂号 | 可选科室、查看 7 天号源、成功预约并取消 | ✅ 含幂等与满号 400 |
| AC-8 | 记录查询 | 近 7/30/180 天记录可查，弹窗显示完整摘要 | ✅ |
| AC-9 | 合规 | 所有回答均含免责声明且无确诊/处方表述 | ✅ |
| AC-10 | 降级 | 关闭 LLM 后系统仍能返回降级科普结果 | ✅ 关闭 LLM 后验证通过 |

### 9.3 验证覆盖范围

| 层次 | 覆盖内容 |
|---|---|
| 接口层 | 规格书 4.2 全部 19 个端点 + 兼容端点，方法/路径/状态码正确 |
| 业务规则 | 科室归一化（呼吸内科→呼吸科、用药→药学门诊）、幂等、号源扣减、排班可复现、三类场景落库、证据上限 8 条 |
| 边界异常 | 满号 400、重复取消 400、非法科室 400、越界日期 400、会话不存在 404 |
| 合规安全 | 免责声明必含、4 条违规表述替换、Key 不回显 |
| 链路 | 降级模式（无 Key）与真实大模型模式（有 Key，含联网检索）均实测通过 |

---

## 十、已知限制与后续可优化项

| 项 | 说明 |
|---|---|
| 降级回答的表达自然度 | 降级模式由规则摘要知识库原文，覆盖面与流畅度不如真实大模型；配置 Key 后走 ReasoningAgent 效果显著更好 |
| 检索方式 | 字符 n-gram TF-IDF 是无监督字面匹配，同义改写召回有限（已通过同义词表缓解）；如需更强语义可接入向量库与嵌入模型（`DASHSCOPE_EMBEDDING_MODEL` 已预留配置项） |
| 用户体系 | 当前以 `user_id` 字符串区分（前端默认 `demo_user`），未接入登录鉴权与多租户隔离 |
| 报告数据 | 为内置模拟数据（3 份），未对接 LIS/PACS 真实接口 |
| 排班数据 | 由固定种子伪随机生成，未对接 HIS 排班系统 |
| 并发与幂等 | 预约的号源扣减为"查询 + 插入"，高并发下理论存在超额风险，生产环境建议加唯一索引或数据库级约束 |
| 大模型回答合规 | `compliance_guard` 采用关键短语替换，覆盖规格书列出的 4 条模式；更严格的合规可引入独立审查模型（SafetyAgent 已是独立节点，便于替换实现） |

---

## 十一、开发约定

1. **分层职责**：`route/` 只做参数校验与调用；业务逻辑放 `service/`；可复用的纯函数放 `utils/`；Agent 节点只读写 `AgentState`，不直接访问数据库。
2. **状态契约**：新增 Agent 字段必须同时更新 `utils/state.py` 的 `AgentState` 与 `initial_state()`，避免 `graph.invoke` 缺 key。
3. **证据合并**：`evidence` 与 `trace` 使用 `Annotated[List, operator.add]`，RAG 与 Research 并行写入不会互相覆盖。
4. **新增接口**：在 `route/` 下按资源建文件，在 `main.py` 注册 router；请求/响应模型统一放 `route/schemas.py`。
5. **合规红线**：任何新增的用户可见文案都必须经过 `compliance_guard`，且不得出现确诊、处方、具体剂量、绝对化表达。
6. **知识库扩充**：新增 `data/knowledge_base/NN_主题.md`，使用 `# 文档标题` + `## 章节标题` 结构（检索按 `##` 切块，章节标题会作为证据标题展示）；首段建议写"适用症状/适用人群"，有助于相关性判定。
7. **密钥管理**：真实 Key 只放本地 `model/.env` 或系统环境变量，`model/.env.example` 保持占位。
