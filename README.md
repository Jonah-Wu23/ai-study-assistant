# ai-study-assistant

## 简介

ai-study-assistant 是一款基于本地 GraphRAG 构建的 AI 学习辅助平台，支持文档摄取、语义检索与流式对话，帮助用户快速构建个性化知识库并高效完成学习任务。

## 核心功能

- 文档摄取：支持多种文本格式文件导入，自动分片并构建向量索引。
- 语义检索：基于 GraphRAG 引擎，快速定位相关文档片段。
- 智能对话：结合大型语言模型生成回答，支持流式输出（SSE）。
- 话题管理：多会话隔离，支持话题创建、查询与删除。
- 前端交互：直观的聊天 UI，支持文件上传、话题列表和历史记录查看。

## 技术栈

- 后端：FastAPI + Uvicorn
- 检索引擎：GraphRAG 本地化实现
- 存储：本地文件系统（data/、vector_store/、chat_history/）
- 前端：Vite + Vue3/React
- 依赖管理：Python requirements.txt、npm package.json

## 项目结构

第一次运行时，需按照以下项目结构进行构建：
```
ai-study-assistant/
├── backend/
│   ├── main.py                 # FastAPI 应用入口
│   ├── graphrag_processor.py   # GraphRAG 初始化与摄取逻辑
│   ├── storage.py              # 文件存储与话题管理
│   ├── models.py               # 数据模型定义
│   ├── data/                   # 原始文档目录
│   ├── vector_store/           # 向量索引存储
│   ├── embedding_models_cache_zh/ # 嵌入模型缓存
│   ├── chat_history/           # 聊天历史记录
│   ├── .env                    # 环境变量配置
│   └── requirements.txt        # Python 依赖
├── frontend/
│   ├── public/                 # 静态资源
│   ├── src/                    # 前端源码
│   │   └── services/api.js     # API 调用封装
│   ├── vite.config.js          # Vite 配置
│   └── package.json            # 前端依赖与脚本
├── .gitignore
├── README.md
└── run.bat                     # 启动脚本
```

## 安装与运行

需手动创建.env文件在backend\.env
内容如下：
```bash
# .env
COURSE_MATERIAL_DIR=./data
CHAT_HISTORY_DIR=./chat_history
GRAPHRAG_ROOT_DIR=./data # Root for graphrag files

# DeepSeek Credentials (Used by graphrag_processor to create settings.yaml)
DEEPSEEK_API_KEY=YourDeepSeekApiKey
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# PORT=8000 # Optional: Define server port
```

### 后端
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 即可使用前端界面。

第二次使用时，即可使用run.bat直接启动。

## 使用说明

1. 将目标文档放入 `backend/data/` 目录。
2. 调用后端 `/api/ingest` 接口生成检索索引。
3. 在前端聊天界面输入查询，系统会返回相关内容并支持流式对话。
4. 使用 `/api/test-delete/{item_id}` 等测试接口验证删除功能。

## 贡献指南

1. Fork 本仓库
2. 创建分支 `feat/xxx`
3. 提交代码并发起 Pull Request

## 许可证

本项目采用 MIT License，详见 LICENSE 文件。
