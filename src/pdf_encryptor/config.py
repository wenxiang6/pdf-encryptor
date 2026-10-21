"""本地配置：默认密码持久化（不写死在代码里）。"""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR_NAME = ".pdf_encryptor"
CONFIG_FILE_NAME = "config.json"
DEFAULT_PASSWORD_KEY = "default_password"


def config_dir() -> Path:
    return Path.home() / CONFIG_DIR_NAME


def config_path() -> Path:
    return config_dir() / CONFIG_FILE_NAME


def load_default_password() -> str:
    """读本地默认密码；没有配置则返回空字符串。"""
    path = config_path()
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    value = data.get(DEFAULT_PASSWORD_KEY, "")
    return value if isinstance(value, str) else ""


def save_default_password(password: str) -> Path:
    """把当前密码写入本地配置。"""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, json.JSONDecodeError):
            data = {}

    data[DEFAULT_PASSWORD_KEY] = password
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
