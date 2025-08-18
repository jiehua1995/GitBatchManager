# Git Batch Manager

## Project Overview
Git Batch Manager is an efficient tool for managing multiple Git repositories. It provides batch operation capabilities, supports real-time progress and error feedback, and helps developers manage codebases more easily.

### Features
- **Batch Operations**: Perform pull and push operations on multiple Git repositories simultaneously.
- **Real-Time Feedback**: Display operation progress, status, and detailed error messages in real-time.
- **Automatic Detection**: Automatically scan all Git repositories in the specified directory.
- **Internationalization Support**: Multi-language interface support, including English, Simplified Chinese, Traditional Chinese, and German.
- **User-Friendly**: Intuitive interface design, easy to use.

### Advantages
- **Efficiency**: Batch operations save time, ideal for developers managing multiple repositories.
- **Flexibility**: Supports custom operations and multiple language environments.
- **Reliability**: Detailed error messages and suggestions help users quickly locate issues.
- **Cross-Platform**: Supports Windows, macOS, and Linux.

## Environment Setup

### System Requirements
- Python Version: 3.8 or higher
- Operating System: Windows, macOS, or Linux

### Create Virtual Environment
It is recommended to use Conda to create a virtual environment for dependency isolation:

```bash
conda create -n gitmanager python=3.12
conda activate gitmanager
```

### Install Dependencies
Install the required Python packages using the following command:

```bash
pip install PySide6 nuitka argparse imageio
```

## Usage Instructions

### Run the Project
Activate the virtual environment and run the following command to start the software:

```bash
python main.py
```

### Package as Executable

#### Using the Automated Build Script (Recommended)
The project includes a `build.py` script that automatically handles packaging for all platforms with multi-language support:

```bash
python build.py
```

When you run the script, you can choose your preferred language:
- **1. 中文** - Chinese interface
- **2. English** - English interface  
- **3. Deutsch** - German interface

This script will:
- Let you select the interface language (Chinese/English/German)
- Automatically detect your operating system (Windows, macOS, or Linux)
- Find the correct PySide6 plugin paths
- Apply platform-specific packaging options
- Generate the executable in the `dist` folder
- Save a detailed build log to `build.log`

#### Manual Packaging with Nuitka
If you prefer manual packaging, Nuitka is an efficient Python compiler that can compile Python scripts into standalone executables.

##### Windows Platform
Run the following command for packaging:

```bash
python -m nuitka \
  --standalone \
  --onefile \
  --enable-plugin=pyside6 \
  --windows-icon-from-ico=icon.png \
  --windows-console-mode=disable \
  --include-data-dir=<PySide6 plugin path>=PySide6/plugins \
  --include-data-dir=i18n=i18n \
  --output-dir=dist main.py
```

##### macOS/Linux Platform
Run the following command for packaging:

```bash
python -m nuitka \
  --standalone \
  --onefile \
  --enable-plugin=pyside6 \
  --icon=icon.png \
  --include-data-dir=i18n=i18n \
  --output-dir=dist main.py
```

The generated executable file will be located in the `dist` folder.

### Debug Path Issues
If plugin path detection fails, run the following script to manually retrieve the PySide6 plugin path:

```python
import PySide6
import os

print(os.path.join(os.path.dirname(PySide6.__file__), "plugins"))
```

## Internationalization Support
Git Batch Manager supports the following languages:
- English (`en.json`)
- Simplified Chinese (`zh_CN.json`)
- Traditional Chinese (`zh_TW.json`)
- German (`de.json`)

## Author
Jie Hua, 2025
