#!/usr/bin/env python3
"""
测试 build.py 的跨平台功能
"""

import platform
import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build import get_pyside6_plugin_path

def test_platform_detection():
    """测试平台检测"""
    current_os = platform.system()
    print(f"🖥️ 检测到操作系统: {current_os}")
    
    # 模拟不同平台的检测
    platforms = ["Windows", "Darwin", "Linux"]
    for test_os in platforms:
        print(f"\n测试 {test_os} 平台:")
        if test_os == "Windows":
            params = ["--windows-icon-from-ico=icon.png", "--windows-console-mode=disable"]
        elif test_os in ["Darwin", "Linux"]:
            params = ["--icon=icon.png"]
        else:
            params = []
        
        print(f"  特定参数: {params}")

def test_plugin_detection():
    """测试插件路径检测"""
    print("\n🔍 测试 PySide6 插件路径检测:")
    try:
        plugin_paths = get_pyside6_plugin_path()
        if plugin_paths:
            print(f"找到 {len(plugin_paths)} 个有效插件路径")
        else:
            print("未找到插件路径")
    except Exception as e:
        print(f"插件检测失败: {e}")

if __name__ == "__main__":
    print("=== Build.py 跨平台功能测试 ===")
    test_platform_detection()
    test_plugin_detection()
    print("\n✅ 测试完成！")
