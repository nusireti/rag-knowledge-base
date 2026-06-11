"""
Streamlit Cloud 入口文件
部署时 Main file path 填这个文件
"""

import os
import sys

# 确保项目根目录在路径中
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# 直接导入主 UI 模块
from app.web import ui
