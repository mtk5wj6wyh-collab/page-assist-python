#!/bin/bash

# Page Assist Python Edition - 启动脚本

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   Page Assist - Python Edition${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}警告: 未找到python3，使用python${NC}"
    PYTHON=python
else
    PYTHON=python3
fi

# 检查依赖
if ! $PYTHON -c "import streamlit" &> /dev/null; then
    echo -e "${YELLOW}正在安装依赖...${NC}"
    $PYTHON -m pip install -r requirements.txt
fi

# 解析参数
MODE=${1:-streamlit}

case $MODE in
    streamlit|web|ui)
        echo -e "${GREEN}启动 Streamlit 前端...${NC}"
        echo -e "访问地址: http://localhost:8501"
        $PYTHON -m streamlit run app.py --server.port 8501
        ;;
    api|server|backend)
        echo -e "${GREEN}启动 API 服务器...${NC}"
        echo -e "API地址: http://localhost:8000"
        $PYTHON -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
        ;;
    init|setup)
        echo -e "${GREEN}初始化数据库...${NC}"
        $PYTHON main.py --mode init
        ;;
    both)
        echo -e "${GREEN}同时启动前端和API服务器...${NC}"
        # 启动API服务器
        $PYTHON -m uvicorn api:app --host 0.0.0.0 --port 8000 &
        API_PID=$!
        sleep 2
        # 启动Streamlit
        $PYTHON -m streamlit run pages/主页.py --server.port 8501 &
        ST_PID=$!
        echo -e "${GREEN}API服务器 PID: $API_PID${NC}"
        echo -e "${GREEN}Streamlit PID: $ST_PID${NC}"
        echo -e "按 Ctrl+C 停止所有服务"
        wait
        ;;
    help|--help|-h)
        echo "使用方法: $0 [模式]"
        echo ""
        echo "模式选项:"
        echo "  streamlit  (默认) - 启动Streamlit前端"
        echo "  api                  - 启动API服务器"
        echo "  both                 - 同时启动前端和API"
        echo "  init                 - 初始化数据库"
        echo ""
        echo "示例:"
        echo "  $0                  # 启动前端"
        echo "  $0 api              # 启动API服务器"
        echo "  $0 both             # 启动两个服务"
        ;;
    *)
        echo -e "${YELLOW}未知模式: $MODE${NC}"
        echo "使用 $0 help 查看帮助"
        ;;
esac
