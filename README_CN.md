# Git Batch Manager

## 项目简介
Git Batch Manager 是一个高效的工具，用于管理多个 Git 仓库。它提供了批量操作功能，支持实时显示进度和错误信息，帮助开发者更轻松地管理代码库。

### 功能特点
- **批量操作**：支持同时对多个 Git 仓库进行拉取和推送操作。
- **实时反馈**：实时显示操作进度、状态和详细的错误信息。
- **自动检测**：自动扫描指定目录下的所有 Git 仓库。
- **国际化支持**：支持多语言界面，包括英语、简体中文、繁体中文和德语。
- **用户友好**：直观的界面设计，易于使用。

### 软件优势
- **高效**：批量操作节省时间，适合管理多个仓库的开发者。
- **灵活**：支持自定义操作和多种语言环境。
- **可靠**：详细的错误信息和解决建议，帮助用户快速定位问题。
- **跨平台**：支持 Windows、macOS 和 Linux。

## 环境设置

### 系统要求
- Python 版本：3.8 或更高
- 操作系统：Windows、macOS 或 Linux

### 创建虚拟环境
建议使用 Conda 创建虚拟环境以隔离依赖：

```bash
conda create -n gitmanager python=3.12
conda activate gitmanager
```

### 安装依赖
使用以下命令安装必要的 Python 包：

```bash
pip install PySide6 nuitka argparse imageio
```

## 使用说明

### 运行项目
激活虚拟环境后，运行以下命令启动软件：

```bash
python main.py
```

### 打包为可执行文件

#### 使用自动化构建脚本（推荐）
项目包含了一个 `build.py` 脚本，可以自动处理所有平台的打包，并支持多语言界面：

```bash
python build.py
```

运行脚本时，您可以选择喜欢的界面语言：
- **1. 中文** - 中文界面
- **2. English** - 英文界面
- **3. Deutsch** - 德文界面

此脚本将会：
- 让您选择界面语言（中文/英文/德文）
- 自动检测您的操作系统（Windows、macOS 或 Linux）
- 查找正确的 PySide6 插件路径
- 应用平台特定的打包选项
- 在 `dist` 文件夹中生成可执行文件
- 将详细的构建日志保存到 `build.log`

#### 使用 Nuitka 手动打包
如果您更喜欢手动打包，Nuitka 是一个高效的 Python 编译器，可以将 Python 脚本编译为独立的可执行文件。

##### Windows 平台
运行以下命令进行打包：

```bash
python -m nuitka \
  --standalone \
  --onefile \
  --enable-plugin=pyside6 \
  --windows-icon-from-ico=icon.png \
  --windows-console-mode=disable \
  --include-data-dir=<PySide6插件路径>=PySide6/plugins \
  --include-data-dir=i18n=i18n \
  --output-dir=dist main.py
```

##### macOS/Linux 平台
运行以下命令进行打包：

```bash
python -m nuitka \
  --standalone \
  --onefile \
  --enable-plugin=pyside6 \
  --icon=icon.png \
  --include-data-dir=i18n=i18n \
  --output-dir=dist main.py
```

生成的可执行文件将位于 `dist` 文件夹中。

### 调试路径问题
如果插件路径检测失败，可以运行以下脚本手动获取 PySide6 插件路径：

```python
import PySide6
import os

print(os.path.join(os.path.dirname(PySide6.__file__), "plugins"))
```

## 国际化支持
Git Batch Manager 支持以下语言：
- 英语 (`en.json`)
- 简体中文 (`zh_CN.json`)
- 繁体中文 (`zh_TW.json`)
- 德语 (`de.json`)

## 作者
Jie Hua, 2025
