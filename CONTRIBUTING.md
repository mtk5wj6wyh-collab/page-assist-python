# 贡献指南

感谢你对 Page Assist Python Edition 的关注！

## 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/mtk5wj6wyh-collab/page-assist-python.git
cd page-assist-python

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
pip install -e ".[dev]"
```

## 代码规范

- 遵循 PEP 8 代码风格
- 使用 `black` 格式化代码
- 使用 `ruff` 进行代码检查

```bash
black .
ruff check .
```

## 提交规范

- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `refactor`: 代码重构
- `style`: 代码格式调整
- `test`: 测试相关
- `chore`: 构建/工具链更新

## Pull Request 流程

1. Fork 本项目
2. 创建你的特性分支 (`git checkout -b feat/amazing-feature`)
3. 提交你的更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feat/amazing-feature`)
5. 创建一个 Pull Request

## 项目结构说明

| 目录 | 说明 |
|------|------|
| `models/` | SQLAlchemy ORM 数据模型 |
| `services/` | 核心业务逻辑服务 |
| `pages/` | Streamlit 前端页面（数字前缀决定排序） |
| `utils/` | 工具函数和配置存储 |
| `data/` | 运行时数据（自动生成，不入库） |

## 添加新的 AI 提供商

1. 在 `services/ai_provider.py` 中创建新的 Provider 类
2. 继承 `BaseAIProvider` 或 `OpenAIProvider`
3. 实现 `chat()` 和 `chat_stream()` 方法
4. 在 `get_ai_provider()` 工厂函数中注册

## 添加新的搜索引擎

1. 在 `services/search.py` 中创建新的 Search 类
2. 继承 `BaseSearchProvider`
3. 实现 `search()` 方法
4. 在 `get_search_provider()` 工厂函数中注册

## 问题反馈

请通过 GitHub Issues 提交问题，包含：
- 运行环境（Python 版本、操作系统）
- 重现步骤
- 期望行为 vs 实际行为
- 错误日志
