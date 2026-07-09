#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
initialization.py - 初始化和全局变量设置

负责设置全局路径变量和初始化工作流
"""

from pathlib import Path

from dotenv import load_dotenv

# 日志配置

setup_global_finished: bool = False

__all__ = [
    # 初始化函数
    "setup_globals",
    "setup_global_finished",
]


def setup_globals() -> None:
    """
    设置全局路径变量

    必须在调用任何工作流函数之前调用
    """

    # 加载环境变量
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"已加载环境变量：{env_path}")
    else:
        print("警告：未找到.env 文件，请确保环境变量已设置")

    global setup_global_finished

    setup_global_finished = True
