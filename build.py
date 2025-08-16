import os
import subprocess
import platform
import PySide6
import json


# 多语言文本定义
MESSAGES = {
    "zh_CN": {
        "select_language": "请选择语言 / Please select language / Bitte wählen Sie eine Sprache:",
        "options": "1. 中文\n2. English\n3. Deutsch",
        "enter_choice": "请输入选择 (1-3): ",
        "invalid_choice": "无效选择，使用默认中文",
        "detecting_paths": "🔍 正在检测以下候选路径:",
        "path_exists": "存在",
        "path_not_exists": "不存在",
        "no_plugin_found": "⚠ 未找到插件目录，可能 PySide6 安装不完整，或 Nuitka 自带插件。",
        "detected_os": "🖥️ 检测到操作系统:",
        "start_packaging": "开始打包...",
        "added_windows_params": "✅ 已添加 Windows 特定参数",
        "added_platform_params": "✅ 已添加 {} 特定参数",
        "unknown_os": "⚠️ 未识别的操作系统: {}，使用默认参数",
        "plugin_added": "✅ 插件路径已添加到命令: {} -> PySide6/{}",
        "i18n_added": "✅ 语言文件路径已添加到命令: i18n",
        "final_command": "🔧 最终打包命令:",
        "build_success": "✅ 打包成功，可执行文件已生成在 dist 文件夹中。",
        "build_failed": "❌ 打包失败，错误码: {}",
        "log_saved": "📄 完整日志已保存到 {}"
    },
    "en": {
        "select_language": "请选择语言 / Please select language / Bitte wählen Sie eine Sprache:",
        "options": "1. 中文\n2. English\n3. Deutsch",
        "enter_choice": "Enter your choice (1-3): ",
        "invalid_choice": "Invalid choice, using default English",
        "detecting_paths": "🔍 Detecting candidate paths:",
        "path_exists": "exists",
        "path_not_exists": "not exists",
        "no_plugin_found": "⚠ Plugin directory not found, PySide6 installation may be incomplete, or Nuitka has built-in plugins.",
        "detected_os": "🖥️ Detected operating system:",
        "start_packaging": "Starting packaging...",
        "added_windows_params": "✅ Added Windows-specific parameters",
        "added_platform_params": "✅ Added {}-specific parameters",
        "unknown_os": "⚠️ Unknown operating system: {}, using default parameters",
        "plugin_added": "✅ Plugin path added to command: {} -> PySide6/{}",
        "i18n_added": "✅ Language files path added to command: i18n",
        "final_command": "🔧 Final packaging command:",
        "build_success": "✅ Build successful, executable generated in dist folder.",
        "build_failed": "❌ Build failed, error code: {}",
        "log_saved": "📄 Complete log saved to {}"
    },
    "de": {
        "select_language": "请选择语言 / Please select language / Bitte wählen Sie eine Sprache:",
        "options": "1. 中文\n2. English\n3. Deutsch",
        "enter_choice": "Geben Sie Ihre Wahl ein (1-3): ",
        "invalid_choice": "Ungültige Auswahl, verwende Standard Deutsch",
        "detecting_paths": "🔍 Erkenne Kandidatenpfade:",
        "path_exists": "existiert",
        "path_not_exists": "existiert nicht",
        "no_plugin_found": "⚠ Plugin-Verzeichnis nicht gefunden, PySide6-Installation möglicherweise unvollständig oder Nuitka hat eingebaute Plugins.",
        "detected_os": "🖥️ Erkanntes Betriebssystem:",
        "start_packaging": "Beginne mit dem Verpacken...",
        "added_windows_params": "✅ Windows-spezifische Parameter hinzugefügt",
        "added_platform_params": "✅ {}-spezifische Parameter hinzugefügt",
        "unknown_os": "⚠️ Unbekanntes Betriebssystem: {}, verwende Standardparameter",
        "plugin_added": "✅ Plugin-Pfad zum Befehl hinzugefügt: {} -> PySide6/{}",
        "i18n_added": "✅ Sprachdateien-Pfad zum Befehl hinzugefügt: i18n",
        "final_command": "🔧 Finaler Verpackungsbefehl:",
        "build_success": "✅ Build erfolgreich, ausführbare Datei im dist-Ordner generiert.",
        "build_failed": "❌ Build fehlgeschlagen, Fehlercode: {}",
        "log_saved": "📄 Vollständiges Log gespeichert in {}"
    }
}


def select_language():
    """选择语言"""
    print(MESSAGES["zh_CN"]["select_language"])
    print(MESSAGES["zh_CN"]["options"])
    
    try:
        choice = input(MESSAGES["zh_CN"]["enter_choice"])
        if choice == "1":
            return "zh_CN"
        elif choice == "2":
            return "en"
        elif choice == "3":
            return "de"
        else:
            print(MESSAGES["zh_CN"]["invalid_choice"])
            return "zh_CN"
    except (KeyboardInterrupt, EOFError):
        return "zh_CN"


def get_message(lang, key, *args):
    """获取指定语言的消息"""
    message = MESSAGES[lang].get(key, MESSAGES["en"].get(key, key))
    if args:
        return message.format(*args)
    return message


def get_pyside6_plugin_path(lang="zh_CN"):
    """获取 PySide6 插件路径"""
    base_path = os.path.dirname(PySide6.__file__)
    candidates = [
        ("plugins", os.path.join(base_path, "plugins")),
        ("Qt/plugins", os.path.join(base_path, "Qt", "plugins")),
        ("Qt6/plugins", os.path.join(base_path, "Qt6", "plugins")),
        ("qt-plugins", os.path.join(base_path, "qt-plugins")),
    ]
    print(get_message(lang, "detecting_paths"))
    valid_paths = []
    for rel, path in candidates:
        if os.path.exists(path):
            print(f"  ✅ {path}  ({get_message(lang, 'path_exists')})")
            valid_paths.append((rel, path))
        else:
            print(f"  ❌ {path}  ({get_message(lang, 'path_not_exists')})")
    if not valid_paths:
        print(get_message(lang, "no_plugin_found"))
    return valid_paths


def build_executable():
    """使用 Nuitka 打包为可执行文件"""
    # 选择语言
    lang = select_language()
    
    current_os = platform.system()
    plugin_paths = get_pyside6_plugin_path(lang)

    print(get_message(lang, "detected_os"), current_os)
    print(get_message(lang, "start_packaging"))

    command = [
        "python", "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--enable-plugin=pyside6",
        "--output-dir=dist",
        "main.py"
    ]

    # 根据操作系统添加特定参数
    if current_os == "Windows":
        command.extend([
            "--windows-icon-from-ico=icon.png",
            "--windows-console-mode=disable"
        ])
        print(get_message(lang, "added_windows_params"))
    elif current_os in ["Darwin", "Linux"]:  # Darwin 是 macOS 的系统名
        command.append("--icon=icon.png")
        print(get_message(lang, "added_platform_params", current_os))
    else:
        print(get_message(lang, "unknown_os", current_os))

    if plugin_paths:
        for rel, path in plugin_paths:
            command.append(f"--include-data-dir={path}=PySide6/{rel}")
            print(get_message(lang, "plugin_added", path, rel))

    command.append("--include-data-dir=i18n=i18n")
    print(get_message(lang, "i18n_added"))

    print(get_message(lang, "final_command"))
    print(" ".join(command))

    log_file = "build.log"
    with open(log_file, "w", encoding="utf-8") as log:
        # 使用 Popen 实现实时输出
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process.stdout.readline, ''):
            print(line, end='')   # 输出到终端
            log.write(line)       # 写入日志
        process.stdout.close()
        retcode = process.wait()

        if retcode == 0:
            print(get_message(lang, "build_success"))
        else:
            print(get_message(lang, "build_failed", retcode))

        print(get_message(lang, "log_saved", log_file))


if __name__ == "__main__":
    build_executable()
