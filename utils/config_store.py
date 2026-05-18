"""
配置持久化工具 — 使用 JSON 文件存储设置
在 settings page 保存时写入，config.py 启动时读取
"""
import os
import json
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = Path(__file__).parent / ".pageassist_config.json"


def save_config(values: Dict[str, str]):
    """保存配置到 JSON 文件"""
    data = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data.update(values)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # 同时同步到 os.environ（pydantic-settings 会读取）
    for k, v in values.items():
        os.environ[k] = str(v)


def load_config() -> Dict[str, str]:
    """从 JSON 文件加载配置到 os.environ，返回原始数据"""
    if not CONFIG_FILE.exists():
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        for k, v in data.items():
            os.environ[k] = str(v)
        return data
    except (json.JSONDecodeError, OSError):
        return {}
