"""
配置管理模块
负责读取.env文件中的环境变量，统一管理API Key等敏感配置
"""
import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 统一管理配置项
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
PORT = int(os.getenv("PORT", "8000"))