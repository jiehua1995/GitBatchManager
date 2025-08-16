#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Git Batch Manager - A tool for managing multiple Git repositories
Author: Jie Hua, 2025
"""
import os
import sys
import json
import locale
import subprocess
import platform
from pathlib import Path
from functools import partial

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QLabel, QProgressBar, QTextEdit, QCheckBox,
    QMenu, QMessageBox, QSplitter, QAbstractItemView, QComboBox
)
from PySide6.QtGui import QIcon, QColor, QFont, QPixmap, QAction, QDesktopServices
from PySide6.QtCore import (
    Qt, QThread, Signal, QSettings, QTranslator, QLocale,
    QCoreApplication, QDir, QUrl, QDateTime
)




class GitWorker(QThread):
    """Worker thread for Git operations"""
    update_signal = Signal(str, str, str)  # repo_path, message, status
    progress_signal = Signal(int, int)  # current, total
    finished_signal = Signal()

    def __init__(self, repos, operation):
        super().__init__()
        self.repos = repos
        self.operation = operation  # 'pull' or 'push'
        self.running = True

    def run(self):
        total = len(self.repos)
        for i, repo_path in enumerate(self.repos):
            if not self.running:
                break

            repo_name = os.path.basename(repo_path)
            self.progress_signal.emit(i + 1, total)

            # Prepare the command
            if self.operation == 'pull':
                cmd = ['git', 'pull']
            else:  # push
                cmd = ['git', 'push']

            try:
                # Change to the repository directory
                self.update_signal.emit(repo_path, f"Starting {self.operation} for {repo_name}...", "running")
                
                # Get current branch information before operation
                branch_cmd = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
                branch_process = subprocess.run(branch_cmd, cwd=repo_path, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                current_branch = branch_process.stdout.strip() if branch_process.returncode == 0 else "unknown"
                
                # Get current commit hash before operation
                hash_cmd = ['git', 'rev-parse', '--short', 'HEAD']
                hash_process = subprocess.run(hash_cmd, cwd=repo_path, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                before_commit = hash_process.stdout.strip() if hash_process.returncode == 0 else "unknown"
                
                # Execute the Git command
                process = subprocess.Popen(
                    cmd,
                    cwd=repo_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Read output in real-time
                output_lines = []
                while process.poll() is None:
                    stdout_line = process.stdout.readline()
                    if stdout_line:
                        line = stdout_line.strip()
                        output_lines.append(line)
                        self.update_signal.emit(repo_path, line, "running")
                    
                    stderr_line = process.stderr.readline()
                    if stderr_line:
                        line = stderr_line.strip()
                        self.update_signal.emit(repo_path, line, "error")
                
                # Get remaining output
                stdout, stderr = process.communicate()
                if stdout:
                    lines = stdout.strip().split('\n')
                    for line in lines:
                        if line and line not in output_lines:
                            output_lines.append(line)
                            self.update_signal.emit(repo_path, line, "running")
                            
                if stderr:
                    lines = stderr.strip().split('\n')
                    for line in lines:
                        if line:
                            self.update_signal.emit(repo_path, line, "error")
                
                # Check return code
                if process.returncode == 0:
                    # Get new commit hash after operation
                    hash_process = subprocess.run(hash_cmd, cwd=repo_path, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    after_commit = hash_process.stdout.strip() if hash_process.returncode == 0 else "unknown"
                    
                    # Check if anything changed
                    if before_commit != after_commit and before_commit != "unknown" and after_commit != "unknown":
                        # Get commit count difference
                        count_cmd = ['git', 'rev-list', '--count', f"{before_commit}..{after_commit}"]
                        count_process = subprocess.run(count_cmd, cwd=repo_path, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        commit_count = count_process.stdout.strip() if count_process.returncode == 0 else "?"
                        
                        self.update_signal.emit(
                            repo_path, 
                            f"{self.operation.capitalize()} completed successfully on branch '{current_branch}'. "
                            f"Changed from {before_commit} to {after_commit} ({commit_count} new commits)", 
                            "success"
                        )
                    else:
                        self.update_signal.emit(
                            repo_path, 
                            f"{self.operation.capitalize()} completed successfully on branch '{current_branch}'. "
                            f"No new changes.", 
                            "success"
                        )
                else:
                    # Provide more detailed error information
                    error_msg = f"{self.operation.capitalize()} failed with code {process.returncode}"
                    
                    # Add more context based on common error patterns
                    if any("Permission denied" in line for line in output_lines):
                        error_msg += ". Permission error: Check your SSH keys or credentials."
                    elif any("Authentication failed" in line for line in output_lines):
                        error_msg += ". Authentication failed: Check your username/password or SSH keys."
                    elif any("Could not resolve host" in line for line in output_lines):
                        error_msg += ". Network error: Could not resolve host. Check your network connection."
                    elif any("conflict" in line.lower() for line in output_lines):
                        error_msg += ". Merge conflict detected: Please resolve conflicts manually."
                    
                    self.update_signal.emit(repo_path, error_msg, "error")
            
            except Exception as e:
                detailed_error = f"Error: {str(e)}"
                self.update_signal.emit(repo_path, detailed_error, "error")
                self.update_signal.emit(repo_path, f"Exception occurred during {self.operation} operation. Check repository access and network.", "error")
        
        self.finished_signal.emit()

    def stop(self):
        self.running = False


class GitRepoScanner(QThread):
    """Thread for scanning directories for Git repositories"""
    repo_found_signal = Signal(str, str, str, str, str, str, str, str)  # repo_name, repo_path, branch, status, last_commit, author, remote_url, sync_status
    finished_signal = Signal()

    def __init__(self, parent_dir):
        super().__init__()
        self.parent_dir = parent_dir
        self.running = True

    def run(self):
        try:
            # List all subdirectories
            with os.scandir(self.parent_dir) as entries:
                subdirs = [entry.path for entry in entries if entry.is_dir()]
            
            for subdir in subdirs:
                if not self.running:
                    break
                
                # Check if it's a Git repository
                git_dir = os.path.join(subdir, '.git')
                if os.path.isdir(git_dir):
                    repo_name = os.path.basename(subdir)
                    repo_path = subdir
                    
                    # Get current branch
                    try:
                        process = subprocess.run(
                            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        branch = process.stdout.strip()
                    except subprocess.SubprocessError:
                        branch = "unknown"
                    
                    # Get repository status
                    try:
                        process = subprocess.run(
                            ['git', 'status', '--porcelain'],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        status = "clean" if not process.stdout.strip() else "modified"
                    except subprocess.SubprocessError:
                        status = "unknown"
                    
                    # Get sync status with remote
                    sync_status = self.get_sync_status(repo_path, branch)
                    
                    # Get last commit info
                    try:
                        process = subprocess.run(
                            ['git', 'log', '-1', '--format=%cd|%an', '--date=format:%Y-%m-%d %H:%M:%S'],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        commit_info = process.stdout.strip().split('|')
                        last_commit = commit_info[0] if len(commit_info) > 0 else ""
                        author = commit_info[1] if len(commit_info) > 1 else ""
                    except subprocess.SubprocessError:
                        last_commit = ""
                        author = ""
                    
                    # Get remote URL
                    try:
                        process = subprocess.run(
                            ['git', 'remote', 'get-url', 'origin'],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        remote_url = process.stdout.strip()
                        # Convert SSH URLs to HTTPS for hyperlinks
                        if remote_url.startswith("git@"):
                            parts = remote_url.split(":", 1)
                            if len(parts) > 1:
                                domain = parts[0].replace("git@", "")
                                path = parts[1]
                                if path.endswith(".git"):
                                    path = path[:-4]
                                remote_url = f"https://{domain}/{path}"
                    except subprocess.SubprocessError:
                        remote_url = ""
                    
                    self.repo_found_signal.emit(repo_name, repo_path, branch, status, last_commit, author, remote_url, sync_status)
        
        except Exception as e:
            print(f"Error scanning repositories: {str(e)}")
        
        finally:
            self.finished_signal.emit()

    def get_sync_status(self, repo_path, branch):
        """Get synchronization status with remote repository"""
        try:
            # First, try to fetch from remote to get latest remote state
            fetch_process = subprocess.run(
                ['git', 'fetch', '--dry-run'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,  # Add timeout to prevent hanging
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Check if remote branch exists
            remote_branch = f"origin/{branch}"
            remote_check = subprocess.run(
                ['git', 'rev-parse', '--verify', remote_branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if remote_check.returncode != 0:
                return "no_remote"
            
            # Get local and remote commit hashes
            local_hash = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            remote_hash = subprocess.run(
                ['git', 'rev-parse', remote_branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if local_hash.returncode != 0 or remote_hash.returncode != 0:
                return "unknown"
            
            local_commit = local_hash.stdout.strip()
            remote_commit = remote_hash.stdout.strip()
            
            if local_commit == remote_commit:
                return "synced"
            
            # Check if local is ahead of remote
            ahead_check = subprocess.run(
                ['git', 'rev-list', '--count', f"{remote_branch}..HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Check if local is behind remote
            behind_check = subprocess.run(
                ['git', 'rev-list', '--count', f"HEAD..{remote_branch}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if ahead_check.returncode == 0 and behind_check.returncode == 0:
                ahead_count = int(ahead_check.stdout.strip() or 0)
                behind_count = int(behind_check.stdout.strip() or 0)
                
                if ahead_count > 0 and behind_count > 0:
                    return f"diverged"  # Both ahead and behind
                elif ahead_count > 0:
                    return f"ahead"  # Local is ahead
                elif behind_count > 0:
                    return f"behind"  # Local is behind
                else:
                    return "synced"
            
        except (subprocess.SubprocessError, subprocess.TimeoutExpired, ValueError):
            pass
        
        return "unknown"

    def stop(self):
        self.running = False


class GitBatchManager(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        
        # Initialize settings
        self.settings = QSettings("JieHua", "GitBatchManager")
        
        # Initialize translator
        self.translator = QTranslator()
        
        # Initialize UI
        self.init_ui()
        
        # Load language
        self.load_language()
        
        # Load last directory
        last_dir = self.settings.value("last_directory", "")
        if last_dir and os.path.isdir(last_dir):
            self.log_message(f"Loading last used directory: {last_dir}", "info")
            self.scan_repositories(last_dir)
    
    def init_ui(self):
        # Set window properties
        self.setWindowTitle(self.tr("app_title"))
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Top toolbar
        toolbar_layout = QHBoxLayout()
        
        # Select folder button
        self.select_folder_btn = QPushButton(self.tr("select_folder"))
        self.select_folder_btn.clicked.connect(self.select_folder)
        toolbar_layout.addWidget(self.select_folder_btn)
        
        # Pull button
        self.pull_btn = QPushButton(self.tr("pull"))
        self.pull_btn.clicked.connect(lambda: self.batch_operation('pull'))
        toolbar_layout.addWidget(self.pull_btn)
        
        # Push button
        self.push_btn = QPushButton(self.tr("push"))
        self.push_btn.clicked.connect(lambda: self.batch_operation('push'))
        toolbar_layout.addWidget(self.push_btn)
        
        # Language menu
        self.language_menu = QMenu(self.tr("language"))
        
        # Add language actions
        self.lang_actions = {}
        for lang_code, lang_name in [
            ("en", "English"),
            ("zh_CN", "简体中文"),
            ("zh_TW", "繁體中文"),
            ("de", "Deutsch")
        ]:
            action = QAction(lang_name, self)
            action.setCheckable(True)
            action.triggered.connect(partial(self.change_language, lang_code))
            self.language_menu.addAction(action)
            self.lang_actions[lang_code] = action
        
        # Language button
        self.language_btn = QPushButton(self.tr("language"))
        self.language_btn.setMenu(self.language_menu)
        toolbar_layout.addWidget(self.language_btn)
        
        # About button
        self.about_btn = QPushButton(self.tr("about"))
        self.about_btn.clicked.connect(self.show_about)
        toolbar_layout.addWidget(self.about_btn)
        
        # Add toolbar to main layout
        main_layout.addLayout(toolbar_layout)
        
        # Create splitter for table and logs
        splitter = QSplitter(Qt.Vertical)
        
        # Repository table
        self.repo_table = QTableWidget(0, 8)  # Checkbox, Name, Path, Branch, Status, Sync Status, Last Commit, Author, Remote URL
        self.repo_table.setHorizontalHeaderLabels([
            "", self.tr("repo_name"), self.tr("repo_path"),
            self.tr("branch"), self.tr("status"), self.tr("sync_status"), self.tr("last_commit"),
            self.tr("author"), self.tr("remote_url")
        ])
        
        # Set table properties
        self.repo_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.repo_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.repo_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.repo_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.repo_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.repo_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.repo_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.repo_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.repo_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.repo_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.repo_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Connect table cell click event
        self.repo_table.cellClicked.connect(self.handle_cell_click)
        
        # Selection buttons
        selection_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton(self.tr("select_all"))
        self.select_all_btn.clicked.connect(self.select_all_repos)
        selection_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton(self.tr("deselect_all"))
        self.deselect_all_btn.clicked.connect(self.deselect_all_repos)
        selection_layout.addWidget(self.deselect_all_btn)
        
        # Add filter by sync status
        sync_filter_label = QLabel(self.tr("filter_by_sync"))
        selection_layout.addWidget(sync_filter_label)
        
        self.sync_filter_combo = QComboBox()
        self.sync_filter_combo.addItem(self.tr("filter_all"), "all")
        self.sync_filter_combo.addItem(self.tr("sync_behind"), "behind")
        self.sync_filter_combo.addItem(self.tr("sync_ahead"), "ahead")
        self.sync_filter_combo.addItem(self.tr("sync_diverged"), "diverged")
        self.sync_filter_combo.addItem(self.tr("sync_synced"), "synced")
        self.sync_filter_combo.addItem(self.tr("sync_no_remote"), "no_remote")
        self.sync_filter_combo.currentTextChanged.connect(self.apply_sync_filter)
        selection_layout.addWidget(self.sync_filter_combo)
        
        selection_layout.addStretch()
        
        # Add table and selection buttons to a container
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.addWidget(self.repo_table)
        table_layout.addLayout(selection_layout)
        
        # Add table container to splitter
        splitter.addWidget(table_container)
        
        # Log panel and progress bar
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        
        # Log label
        log_label = QLabel(self.tr("logs"))
        log_layout.addWidget(log_label)
        
        # Log text edit
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # Progress bar
        progress_layout = QHBoxLayout()
        progress_label = QLabel(self.tr("progress"))
        progress_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        log_layout.addLayout(progress_layout)
        
        # Add log container to splitter
        splitter.addWidget(log_container)
        
        # Set initial splitter sizes
        splitter.setSizes([400, 200])
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Copyright label
        copyright_label = QLabel("© Jie Hua, 2025")
        copyright_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(copyright_label)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Initialize repository data
        self.repositories = {}
        
        # Initialize worker threads
        self.git_worker = None
        self.scanner = None
        
        # Update language action
        current_locale = QLocale().name()
        if current_locale.startswith("zh_CN"):
            self.lang_actions["zh_CN"].setChecked(True)
        elif current_locale.startswith("zh_TW"):
            self.lang_actions["zh_TW"].setChecked(True)
        elif current_locale.startswith("de"):
            self.lang_actions["de"].setChecked(True)
        else:
            self.lang_actions["en"].setChecked(True)
    
    def select_folder(self):
        """Open a folder selection dialog"""
        last_dir = self.settings.value("last_directory", QDir.homePath())
        directory = QFileDialog.getExistingDirectory(self, self.tr("select_folder"), last_dir)
        
        if directory:
            # Save the selected directory for next time
            self.settings.setValue("last_directory", directory)
            self.settings.sync()  # Ensure settings are saved immediately
            self.scan_repositories(directory)
    
    def scan_repositories(self, directory):
        """Scan the selected directory for Git repositories"""
        # Clear existing data
        self.repositories = {}
        self.repo_table.setRowCount(0)
        self.log_text.clear()
        
        # Log the scanning operation
        self.log_message(f"Scanning for Git repositories in: {directory}", "info")
        
        # Start the scanner thread
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop()
            self.scanner.wait()
        
        self.scanner = GitRepoScanner(directory)
        self.scanner.repo_found_signal.connect(self.add_repository)
        self.scanner.finished_signal.connect(self.scan_finished)
        self.scanner.start()
    
    def add_repository(self, repo_name, repo_path, branch, status, last_commit, author, remote_url, sync_status):
        """Add a repository to the table"""
        # Store repository data
        self.repositories[repo_path] = {
            'name': repo_name,
            'branch': branch,
            'status': status,
            'sync_status': sync_status,
            'last_commit': last_commit,
            'author': author,
            'remote_url': remote_url
        }
        
        # Add to table
        row = self.repo_table.rowCount()
        self.repo_table.insertRow(row)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox_cell = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_cell)
        checkbox_layout.addWidget(checkbox)
        checkbox_layout.setAlignment(Qt.AlignCenter)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.repo_table.setCellWidget(row, 0, checkbox_cell)
        
        # Repository name
        self.repo_table.setItem(row, 1, QTableWidgetItem(repo_name))
        
        # Repository path
        self.repo_table.setItem(row, 2, QTableWidgetItem(repo_path))
        
        # Branch
        self.repo_table.setItem(row, 3, QTableWidgetItem(branch))
        
        # Status
        status_item = QTableWidgetItem(self.tr(f"status_{status}"))
        if status == "clean":
            status_item.setForeground(QColor(0, 128, 0))  # Green
        elif status == "modified":
            status_item.setForeground(QColor(255, 128, 0))  # Orange
        else:
            status_item.setForeground(QColor(128, 128, 128))  # Gray
        self.repo_table.setItem(row, 4, status_item)
        
        # Sync status
        sync_status_item = QTableWidgetItem(self.tr(f"sync_{sync_status}"))
        if sync_status == "synced":
            sync_status_item.setForeground(QColor(0, 128, 0))  # Green
        elif sync_status == "behind":
            sync_status_item.setForeground(QColor(255, 0, 0))  # Red
        elif sync_status == "ahead":
            sync_status_item.setForeground(QColor(0, 0, 255))  # Blue
        elif sync_status == "diverged":
            sync_status_item.setForeground(QColor(128, 0, 128))  # Purple
        elif sync_status == "no_remote":
            sync_status_item.setForeground(QColor(128, 128, 128))  # Gray
        else:  # unknown
            sync_status_item.setForeground(QColor(128, 128, 128))  # Gray
        self.repo_table.setItem(row, 5, sync_status_item)
        
        # Last commit
        self.repo_table.setItem(row, 6, QTableWidgetItem(last_commit))
        
        # Author
        self.repo_table.setItem(row, 7, QTableWidgetItem(author))
        
        # Remote URL
        url_item = QTableWidgetItem(remote_url)
        if remote_url:
            url_item.setForeground(QColor(0, 0, 255))  # Blue for hyperlink
            font = QFont()
            font.setUnderline(True)
            url_item.setFont(font)
        self.repo_table.setItem(row, 8, url_item)
        
        # Log the found repository
        sync_info = f" [{self.tr(f'sync_{sync_status}')}]" if sync_status != "unknown" else ""
        self.log_message(f"Found Git repository: {repo_name} ({branch}){sync_info}", "info")
    
    def scan_finished(self):
        """Called when repository scanning is complete"""
        count = self.repo_table.rowCount()
        self.log_message(f"Scan complete. Found {count} Git repositories.", "success")
    
    def select_all_repos(self):
        """Select all repositories"""
        for row in range(self.repo_table.rowCount()):
            checkbox = self.repo_table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)
    
    def deselect_all_repos(self):
        """Deselect all repositories"""
        for row in range(self.repo_table.rowCount()):
            checkbox = self.repo_table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)
    
    def get_selected_repos(self):
        """Get a list of selected repository paths"""
        selected_repos = []
        for row in range(self.repo_table.rowCount()):
            checkbox = self.repo_table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                repo_path = self.repo_table.item(row, 2).text()
                selected_repos.append(repo_path)
        return selected_repos
    
    def batch_operation(self, operation):
        """Start a batch Git operation (pull or push)"""
        selected_repos = self.get_selected_repos()
        
        if not selected_repos:
            QMessageBox.warning(self, self.tr("app_title"),
                               "Please select at least one repository.")
            return
        
        # Disable buttons during operation
        self.set_buttons_enabled(False)
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        
        # Log the operation
        op_name = "pull" if operation == "pull" else "push"
        self.log_message(f"Starting batch {op_name} operation on {len(selected_repos)} repositories...", "info")
        
        # Start the worker thread
        if self.git_worker and self.git_worker.isRunning():
            self.git_worker.stop()
            self.git_worker.wait()
        
        self.git_worker = GitWorker(selected_repos, operation)
        self.git_worker.update_signal.connect(self.update_repo_status)
        self.git_worker.progress_signal.connect(self.update_progress)
        self.git_worker.finished_signal.connect(self.operation_finished)
        self.git_worker.start()
    
    def update_repo_status(self, repo_path, message, status):
        """Update repository status and log"""
        # Update the log
        repo_name = self.repositories.get(repo_path, {}).get('name', os.path.basename(repo_path))
        self.log_message(f"[{repo_name}] {message}", status)
        
        # Update the status in the table
        for row in range(self.repo_table.rowCount()):
            if self.repo_table.item(row, 2).text() == repo_path:
                if status == "success":
                    self.repositories[repo_path]['status'] = "clean"
                    status_item = QTableWidgetItem("clean")
                    status_item.setForeground(QColor(0, 128, 0))  # Green
                elif status == "error":
                    status_item = QTableWidgetItem("error")
                    status_item.setForeground(QColor(255, 0, 0))  # Red
                else:
                    continue  # Don't update for intermediate messages
                
                self.repo_table.setItem(row, 4, status_item)
                break
    
    def update_progress(self, current, total):
        """Update the progress bar"""
        percentage = int(current * 100 / total) if total > 0 else 0
        self.progress_bar.setValue(percentage)
    
    def operation_finished(self):
        """Called when a batch operation is complete"""
        self.log_message("Batch operation completed.", "success")
        self.set_buttons_enabled(True)
    
    def set_buttons_enabled(self, enabled):
        """Enable or disable buttons during operations"""
        self.select_folder_btn.setEnabled(enabled)
        self.pull_btn.setEnabled(enabled)
        self.push_btn.setEnabled(enabled)
    
    def apply_sync_filter(self):
        """Apply filter based on sync status"""
        filter_value = self.sync_filter_combo.currentData()
        
        for row in range(self.repo_table.rowCount()):
            should_show = True
            
            if filter_value != "all":
                sync_status_item = self.repo_table.item(row, 5)
                if sync_status_item:
                    repo_path = self.repo_table.item(row, 2).text()
                    repo_sync_status = self.repositories.get(repo_path, {}).get('sync_status', 'unknown')
                    should_show = repo_sync_status == filter_value
            
            self.repo_table.setRowHidden(row, not should_show)

    def log_message(self, message, level="info"):
        """Add a message to the log panel with appropriate formatting and icons"""
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")

        # Define icons for each level
        icons = {
            "error": "❌",
            "success": "✅",
            "warning": "⚠️",
            "running": "🔄",
            "info": "ℹ️"
        }

        # Get the appropriate icon
        icon = icons.get(level, "ℹ️")

        # Format message based on level
        if level == "error":
            formatted_message = f"<span style='color:red; font-weight:bold'>[{timestamp}] {icon} ERROR: {message}</span>"
        elif level == "success":
            formatted_message = f"<span style='color:green; font-size:14pt; font-weight:bold'>[{timestamp}] {icon} SUCCESS: {message}</span>"
        elif level == "warning":
            formatted_message = f"<span style='color:orange; font-weight:bold'>[{timestamp}] {icon} WARNING: {message}</span>"
        elif level == "running":
            formatted_message = f"<span style='color:blue'>[{timestamp}] {icon} RUNNING: {message}</span>"
        else:  # info
            formatted_message = f"<span style='color:black'>[{timestamp}] {icon} INFO: {message}</span>"

        self.log_text.append(formatted_message)
        self.log_text.ensureCursorVisible()
    
    def load_language(self):
        """Load language based on system locale or saved setting"""
        # Get saved language or use system locale
        lang_code = self.settings.value("language", QLocale().name())
        self.change_language(lang_code, save=False)
    
    def change_language(self, lang_code, save=True):
        """Change the application language"""
        # Check if language file exists
        lang_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               f"i18n/{lang_code}.json")
        
        if not os.path.exists(lang_file):
            # Fallback to English
            lang_code = "en"
            lang_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                   "i18n/en.json")
        
        # Save the language setting if requested
        if save:
            self.settings.setValue("language", lang_code)
        
        # Update checked action in menu
        for code, action in self.lang_actions.items():
            action.setChecked(code == lang_code)
        
        # Load translations
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            
            # Update UI text
            self.retranslate_ui()
        except Exception as e:
            print(f"Error loading language file: {str(e)}")
    
    def tr(self, key):
        """Translate a string using the loaded translations"""
        if hasattr(self, 'translations') and key in self.translations:
            return self.translations[key]
        return key
    
    def retranslate_ui(self):
        """Update all UI elements with translated text"""
        # Window title
        self.setWindowTitle(self.tr("app_title"))
        
        # Buttons
        self.select_folder_btn.setText(self.tr("select_folder"))
        self.pull_btn.setText(self.tr("pull"))
        self.push_btn.setText(self.tr("push"))
        self.language_btn.setText(self.tr("language"))
        self.about_btn.setText(self.tr("about"))
        self.select_all_btn.setText(self.tr("select_all"))
        self.deselect_all_btn.setText(self.tr("deselect_all"))
        
        # Table headers
        self.repo_table.setHorizontalHeaderLabels([
            "", self.tr("repo_name"), self.tr("repo_path"),
            self.tr("branch"), self.tr("status"), self.tr("sync_status"),
            self.tr("last_commit"), self.tr("author"), self.tr("remote_url")
        ])
    
    def show_about(self):
        """Show the about dialog"""
        QMessageBox.about(self, self.tr("about"), self.tr("about_text"))
    
    def handle_cell_click(self, row, column):
        """Handle cell click events"""
        # Check if the clicked cell is in the URL column (column 8)
        if column == 8:
            url = self.repo_table.item(row, column).text()
            if url and (url.startswith("http://") or url.startswith("https://")):
                QDesktopServices.openUrl(QUrl(url))
                self.log_message(f"Opening URL: {url}", "info")
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any running threads
        if self.git_worker and self.git_worker.isRunning():
            self.git_worker.stop()
            self.git_worker.wait()
        
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop()
            self.scanner.wait()
        
        # Make sure settings are saved
        self.settings.sync()
        
        # Accept the close event
        event.accept()


def main():
    # Create application
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("GitBatchManager")
    app.setOrganizationName("JieHua")
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    
    # Create and show the main window
    window = GitBatchManager()
    window.show()
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


