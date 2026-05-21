<div align="center">

# 🚀 Page Assist - Python Edition

**基于本地 AI 模型的 Web UI 助手**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)

</div>

一个功能丰富的本地 AI 助手，支持多种大语言模型、RAG 知识库、联网搜索、语音合成等能力。提供 Streamlit Web UI 和 FastAPI 后端两种使用方式。

## ✨ 功能特点

| 功能 | 说明 |
|------|------|
| 🤖 **多 AI 模型支持** | Ollama、OpenAI、Claude、Gemini、Groq、DeepSeek、Mistral、Moonshot 共 8 个提供商 |
| 📚 **RAG 知识库** | 上传 PDF/Word/HTML/TXT 文档，构建私有向量知识库 |
| 🔍 **联网搜索** | DuckDuckGo、Tavily、Brave、SearXNG、Bing 多种搜索后端 |
| 🗣️ **语音合成** | Browser TTS、ElevenLabs、OpenAI TTS、Edge TTS |
| 📝 **提示词管理** | 自定义提示词模板，支持 Copilot 快捷触发 |
| 🔧 **MCP 协议** | 支持 Model Context Protocol 工具集成 |
| 🎨 **现代界面** | Streamlit 驱动，深色/浅色主题切换 |

## 📋 环境要求

- Python 3.10+
- （推荐）[Ollama](https://ollama.com/) - 用于本地模型运行和 Embedding

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/mtk5wj6wyh-collab/page-assist-python.git
cd page-assist-python
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 AI 提供商

复制环境变量模板并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置一个 AI 提供商：

```env
# Ollama（推荐，免费本地运行）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
DEFAULT_PROVIDER=ollama

# 或者使用 OpenAI
# OPENAI_API_KEY=sk-your-key
# DEFAULT_PROVIDER=openai
```

### 4. 初始化数据库

```bash
python main.py --mode init
```

### 5. 启动应用

**方式一：Streamlit Web UI（推荐）**

```bash
# Windows
start.bat

# Linux / macOS
bash start.sh
```

或手动启动：

```bash
python main.py --mode streamlit
# 访问 http://localhost:8501
```

**方式二：API 服务器**

```bash
python main.py --mode api
# API 文档 http://localhost:8000/docs
```

**方式三：同时启动前后端**

```bash
# Windows
start.bat both

# Linux / macOS
bash start.sh both
```

## 🏗️ 项目结构

```
srcpy/
├── main.py                 # 主入口（streamlit/api/init 模式切换）
├── app.py                  # Streamlit 多页面应用
├── api.py                  # FastAPI REST 后端
├── config.py               # Pydantic Settings 配置管理
├── database.py             # SQLAlchemy 异步数据库引擎
├── desktop.py              # 桌面客户端（pywebview）
├── build.py                # PyInstaller 打包脚本
├── models/                 # 数据模型层
│   ├── chat.py            # 聊天会话/消息模型
│   ├── knowledge.py       # 知识库/文档/分块模型
│   ├── prompt.py          # 提示词模型
│   └── settings.py        # 应用设置模型
├── services/              # 核心业务服务
│   ├── ai_provider.py     # 8 个 AI 提供商统一接口
│   ├── chat_manager.py    # 聊天管理（搜索增强 + RAG）
│   ├── rag.py             # ChromaDB 向量检索
│   ├── search.py          # 多搜索引擎
│   ├── tts.py             # TTS 语音合成
│   ├── mcp.py             # MCP 协议实现
│   └── prompt_manager.py  # 提示词管理
├── pages/                 # Streamlit 前端页面
│   ├── 01_聊天.py         # 聊天界面
│   ├── 02_知识库.py       # 知识库管理
│   ├── 03_提示词.py       # 提示词管理
│   ├── 04_设置.py         # 系统设置
│   └── 05_工具.py         # 工具箱
├── utils/                 # 工具函数
│   ├── config_store.py   # JSON 配置持久化
│   ├── file_handler.py   # 文件上传处理
│   └── markdown.py       # Markdown 渲染
└── data/                  # 运行时数据（自动创建）
```

## 📡 API 接口

### 聊天

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/chat` | 发送消息 |
| `POST` | `/api/chat/stream` | 流式对话 (SSE) |
| `GET` | `/api/sessions` | 获取会话列表 |
| `POST` | `/api/sessions` | 创建新会话 |
| `DELETE` | `/api/sessions/{id}` | 删除会话 |

### 知识库

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/knowledge` | 获取知识库列表 |
| `POST` | `/api/knowledge` | 创建知识库 |
| `POST` | `/api/knowledge/{id}/upload` | 上传文档 |
| `POST` | `/api/knowledge/{id}/search` | 检索知识库 |

### 其他

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/search` | 执行网络搜索 |
| `POST` | `/api/tts` | 文字转语音 |
| `GET` | `/api/models` | 获取可用模型列表 |
| `GET` | `/api/prompts` | 获取提示词列表 |

启动 API 后访问 `http://localhost:8000/docs` 查看完整 Swagger 文档。

## 🔧 支持的 AI 提供商

| 提供商 | 需要 API Key | Embedding 支持 |
|--------|-------------|---------------|
| Ollama | ❌ 无需 | ✅ |
| OpenAI | ✅ 需要 | ❌ |
| Anthropic Claude | ✅ 需要 | ❌ |
| Google Gemini | ✅ 需要 | ❌ |
| Groq | ✅ 需要 | ❌ |
| DeepSeek | ✅ 需要 | ❌ |
| Mistral | ✅ 需要 | ❌ |
| Moonshot (Kimi) | ✅ 需要 | ❌ |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 🙏 致谢

本项目是 [Page Assist](https://github.com/n4ze3m/page-assist) 浏览器插件的 Python 重写版本。原项目提供了一个优秀的本地 AI 浏览器助手，本项目将其核心能力移植到 Python 生态，以支持更灵活的部署和使用方式。

感谢 [@n4ze3m](https://github.com/n4ze3m) 和所有原项目贡献者的出色工作！

### 特别赞助

<p align="center">
  <a href="https://mimo.mi.com/" target="_blank">
    <img src="https://cdn.cnbj0.fds.api.mi-img.com/b2c-shopapi-pms/pms_1621497797.71927021.png" alt="Xiaomi MiMo 大模型" width="120">
  </a>
</p>

<p align="center">
  <b>感谢 <a href="https://mimo.mi.com/">Xiaomi MiMo 大模型</a> 慷慨赞助 7 亿 Token！</b>
</p>

<p align="center">
  小米大模型的大力支持为本项目的 AI 能力提供了强有力的资源保障，<br>
  使得开发者和用户能够更自由地体验和探索大语言模型的无限可能。<br>
  我们对小米大模型的开放精神和对开源社区的支持表示衷心的感谢！
</p>

## 📜 License

本项目基于 MIT License 开源，详见 [LICENSE](LICENSE) 文件。

---

<div align="center">
Made with ❤️ by Page Assist Contributors
</div>
