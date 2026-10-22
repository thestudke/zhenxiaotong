# 诊小通 Agent（zhenxiao）

互联网医院智能服务平台，围绕「分诊、问诊、用药、报告、记录、挂号」六类高频医疗服务流程构建闭环。
多 Agent 协作 + RAG 知识库 + 联网增强 + 会话记忆 + 报告解读 + 预约挂号整合在一个系统中。

- 后端：FastAPI + SQLAlchemy + LangGraph（Python 3.11+，本机以 3.10 验证可用）
- 前端：Vue 3 + Vite + Element Plus + Pinia
- 数据库：MySQL 或 SQLite（未配置 MySQL 时自动回落 SQLite）
- 依据文档：《01-需求规格说明书》V1.0（系统版本 v2.1.0）

> 本文件是**快速上手**说明。完整的架构设计、接口清单、数据模型、核心机制与开发约定，
> 见 [项目说明文档.md](项目说明文档.md)。

## 一、启动

### 1. 后端（127.0.0.1:8012）

```bash
cd backend
pip install -r requirements.txt
# 环境变量：复制模板后按需填写（可全部留空，走降级模式）
copy model\.env.example model\.env
python -m uvicorn main:app --host 127.0.0.1 --port 8012
```

- 健康检查：`GET http://127.0.0.1:8012/api/health` → `{"status":"ok"}`
- 接口文档：`http://127.0.0.1:8012/docs`

### 2. 前端（127.0.0.1:5178，规格书 4.1 / AC-2 指定端口）

```bash
cd web
npm install
npm run dev
```

打开 `http://127.0.0.1:5178` 即为工作台。开发环境 `/api` 经 Vite 代理转发到 8012。

> 数据库：默认读取 `model/.env` 的 MySQL 配置；若把 `MYSQL_HOST` 与 `DATABASE_URL`
> 都留空，则自动使用 `backend/zhenxiao.db`（SQLite），无需任何外部依赖。

## 二、功能模块（规格书 2.2）

| 编号 | 模块 | 前端路由 | 入口接口 |
|---|---|---|---|
| M1 | 智能分诊台 | `/triage` | `POST /api/triage` |
| M2 | 线上问诊 | `/chat` | `POST /api/consultation`（通用入口 `POST /api/chat`） |
| M3 | 用药咨询 | `/medication` | `POST /api/medication` |
| M4 | 问诊记录 | `/encounters` | `GET /api/records?user_id&days` |
| M5 | 报告查询 | `/reports` | `GET /api/reports`、`GET /api/reports/{id}/interpret` |
| M6 | 预约挂号 | `/appointments` | `GET /api/appointments/schedule`、`POST/DELETE /api/appointments` |
| M7 | 系统设置 | `/settings` | `GET /api/settings`、`DELETE /api/sessions`（一键清空） |

## 三、多 Agent 推理链路（规格书 3.8）

```
RouterAgent → ContextAgent → ┬→ RAGAgent      (本地知识库召回，并发)
                             └→ ResearchAgent (联网 DeepResearch，并发)
            → ReasoningAgent (结构化 JSON 推理)
            → FormatterAgent (仅输出非法 JSON 时触发修复，最多重试 3 次，退避 0.8s)
            → SafetyAgent    (合规替换 + 科室收敛 + 免责声明)
            ↘ FallbackAgent  (LLM 未启用或修复失败时规则兜底)
```

- `thinking_steps` 为人类可读推理步骤，`trace` 为 `AgentTrace(agent, action, detail, duration_ms)`。
- 未配置大模型时，ReasoningAgent 直接短路到 FallbackAgent，不再空转修复循环。

## 四、接口清单（规格书 4.2，共 19 个）

| 方法 | 路径 |
|---|---|
| GET | `/api/health` |
| POST | `/api/chat`（通用问诊，走 consultation 场景） |
| POST | `/api/triage` |
| POST | `/api/consultation` |
| POST | `/api/medication` |
| GET | `/api/sessions` |
| GET | `/api/sessions/{session_id}/messages`（最多 100 条） |
| DELETE | `/api/sessions/{session_id}` |
| DELETE | `/api/sessions`（清空全部数据） |
| GET | `/api/records?user_id&days` |
| GET | `/api/reports` |
| GET | `/api/reports/{report_id}/interpret` |
| GET | `/api/departments` |
| GET | `/api/appointments/schedule?department&user_id` |
| POST | `/api/appointments` |
| GET | `/api/appointments` |
| DELETE | `/api/appointments/{appointment_id}` |
| GET | `/api/metrics` |
| GET | `/api/settings` |

额外保留 `/api/encounters`（与 `/api/records` 同源）与 `/api/profile/{user_id}`。

## 五、验收核对方式

接口可交互验证：打开 `http://127.0.0.1:8012/docs`，或在系统设置页查看模型/联网状态。

关键路径的验收标准（规格书第 7 章 AC-1~AC-10）建议按以下方式人工核对：

| 验收项 | 核对方式 |
|---|---|
| AC-1 后端启动 | 访问 `GET /api/health` 应返回 `{"status":"ok"}` |
| AC-2 前端启动 | 打开 `http://127.0.0.1:5178` 应正常显示工作台 |
| AC-3 分诊闭环 | 分诊台输入"发热两天、咳嗽有黄痰、体温38.7℃"，应返回科室、风险等级、证据与 Agent 链路 |
| AC-4 问诊记忆 | 同一会话内连续追问，第二条回答应结合上文 |
| AC-5 用药咨询 | 问"布洛芬和感冒灵能一起吃吗"，应返回用药安全参考且不含处方剂量 |
| AC-6 报告解读 | 报告页点击"AI 解读"，应返回异常指标科普与就医建议 |
| AC-7 预约挂号 | 选科室 → 看 7 天号源 → 预约 → 取消，全流程应可用 |
| AC-8 记录查询 | 记录页切换近 7/30/180 天，弹窗应显示完整摘要 |
| AC-9 合规 | 所有回答均含免责声明，且无确诊/处方表述 |
| AC-10 降级 | 清空 `DASHSCOPE_API_KEY_2` 后重启后端，应仍返回科普结果（`/api/settings` 显示 `llm_enabled: false`） |

## 六、常见问题

### 1. 明明配了 Key，为什么还是"降级模式"？

系统环境变量**只在进程启动时读取一次**。在 Windows 上设置了系统/用户环境变量后：

- 已经打开的终端、IDE、Python 进程**不会自动获得**新变量，必须**完全关闭并重新打开**（PyCharm 需重启 IDE，而不是只重启 Run 配置）；
- 用 `$env:NAME = "..."` 设的变量只在当前会话有效。

自检三连（在**启动后端的同一个终端**里执行）：

```powershell
# ① 进程能否看到该变量（为空 = 没继承到）
$env:DASHSCOPE_API_KEY_2

# ② 应用配置是否读到（打印 Key 长度与开关状态）
python -c "from config import settings; from utils import llm; print('key长度:', len(settings.dashscope_api_key_2), 'llm_enabled:', llm.is_enabled())"

# ③ 运行中的服务实际状态
curl http://127.0.0.1:8012/api/settings
# 期望： "llm_enabled": true, "api_key_configured": true
```

变量名对照（系统环境变量名 ↔ 配置字段名，pydantic-settings 忽略大小写）：

| 系统环境变量 | 配置字段 |
|---|---|
| `DASHSCOPE_API_KEY_2` | `dashscope_api_key_2` |
| `DASHSCOPE_BASE_URL` | `dashscope_base_url` |
| `DASHSCOPE_CHAT_MODEL` | `dashscope_chat_model` |
| `TAVILY_API_KEY` | `tavily_api_key` |

优先级：**系统/用户环境变量 > `model/.env`**（同名时环境变量胜出，且字段已显式定义，不受 `extra="ignore"` 影响）。

强制让当前会话立刻拿到系统变量（无需重启终端）：

```powershell
$env:DASHSCOPE_API_KEY_2 = [Environment]::GetEnvironmentVariable('DASHSCOPE_API_KEY_2','Machine')
python -m uvicorn main:app --host 127.0.0.1 --port 8012
```

### 2. 未配置 Key 时会怎样？

系统仍可完整使用（规格书 2.4）：RouterAgent 直接短路到 FallbackAgent，由**本地规则 + RAG 知识库摘要**给出"先解答、后建议"的科普回答，并附免责声明。此时 `/api/settings` 显示 `llm_enabled: false`、回答 `metrics.mode = "fallback"`、`metrics.answer_source = "kb_summary"`。

### 3. `vite build` 报 `EPERM: remove ...esbuild-xxx`？

esbuild 在 Windows 上删临时目录失败的宿主机问题（与项目代码无关）。换普通终端重试，或先 `npm cache clean --force`；开发用 `npm run dev` 不受影响。

### 4. 参考依据里出现"联网检索暂不可用"？

这条是降级占位证据（规格书 3.10），说明 ResearchAgent 这次没拿到真实联网结果。先看服务自报的原因：

```powershell
curl http://127.0.0.1:8012/api/settings
# 关注 deep_search_enabled / deep_search_key_configured /
#      deep_search_available / deep_search_issue
```

| 现象 | 原因 | 解决 |
|---|---|---|
| `deep_search_issue` 提示缺少 `tavily-python` | **当前解释器没装这个包**（最常见：IDE 用 `.venv`，而包装在别的环境里） | 在该解释器下 `pip install tavily-python`；或直接改用已装好依赖的解释器 |
| `deep_search_key_configured: false` | 未配置 Tavily Key | 在 `model/.env` 写 `TAVILY_API_KEY=tvly-xxx`，或设系统环境变量后**重启进程** |
| `deep_search_enabled: false` | 配置里关掉了 | 设 `DEEP_SEARCH_ENABLED=true` |
| 提示"检索失败：…" | 网络不通 / Key 无效 / 配额用尽 | 按提示里的具体异常处理 |

> 关键：**不同 Python 解释器的包不共享**。本项目验证过 `miniconda3`(base) 与 `aiagent\.venv` 两个环境，
> `tavily-python` 必须装进"实际启动后端的那一个"。IDE 里选哪个解释器，就往哪个装依赖。

## 七、目录结构

```
backend/
  main.py            应用入口与路由注册
  config.py          环境变量与数据库 URL
  route/             接口层（chat/scenes/sessions/records/encounters/profile/
                     appointments/reports/settings/metrics/departments/schemas）
  service/           业务编排（chat/memory/session/encounter/appointment/report/profile）
  agent/             LangGraph 多 Agent（graph/router/context/rag/research/
                     reasoning/formatter/safety）
  utils/             模型调用、RAG 检索、规则、合规、兜底、状态契约
  data/knowledge_base/  13 篇本地 Markdown 知识库
web/
  src/views/         7 个功能页面 + 健康档案
  src/api/           接口封装
```
