from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, 
                             QLabel, QLineEdit, QProgressBar, QPlainTextEdit, 
                             QFormLayout, QComboBox, QSpinBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTextEdit, QCheckBox, 
                             QTabWidget, QMainWindow, QStatusBar, QAbstractItemView, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
import os

class RunTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Input:"))
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        file_layout.addWidget(self.file_input)
        
        self.batch_format_cb = QComboBox()
        self.batch_format_cb.addItems([".ass", ".srt", "Both"])
        self.batch_format_cb.setToolTip("Target Format for Folders")
        file_layout.addWidget(self.batch_format_cb)
        
        self.browse_btn = QPushButton("File")
        self.browse_folder_btn = QPushButton("Folder")
        file_layout.addWidget(self.browse_btn)
        file_layout.addWidget(self.browse_folder_btn)
        layout.addLayout(file_layout)
        
        self.lbl_anime = QLabel("Anime: None")
        self.lbl_episode = QLabel("Episode: None")
        layout.addWidget(QLabel("<b>Detected Project</b>"))
        layout.addWidget(self.lbl_anime)
        layout.addWidget(self.lbl_episode)
        
        controls_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.resume_btn = QPushButton("Resume")
        self.stop_btn = QPushButton("Stop")
        self.open_out_btn = QPushButton("Open Folder")
        self.start_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.open_out_btn.setEnabled(False)
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.resume_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.open_out_btn)
        layout.addLayout(controls_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.lbl_chunk = QLabel("Chunk: 0/0")
        self.lbl_status = QLabel("Status: Idle")
        self.lbl_batch = QLabel("Batch Queue: Idle")
        
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.lbl_chunk)
        status_layout.addWidget(self.lbl_status)
        status_layout.addWidget(self.lbl_batch)
        layout.addLayout(status_layout)
        
        self.logs_view = QPlainTextEdit()
        self.logs_view.setReadOnly(True)
        self.logs_view.setMaximumBlockCount(500)
        layout.addWidget(self.logs_view)

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.endswith(('.srt', '.ass')):
                self.file_input.setText(path)

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # --- Main Agent Settings ---
        main_group = QGroupBox("Main Translation Agent")
        main_lay = QFormLayout(main_group)
        
        self.provider_cb = QComboBox()
        self.provider_cb.addItems(["openai", "anthropic", "deepseek", "openrouter", "gemini", "local"])
        main_lay.addRow("Provider:", self.provider_cb)

        
        self.model_name = QComboBox()
        self.model_name.setEditable(True)
        main_lay.addRow("Model Name:", self.model_name)
        
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        main_lay.addRow("API Key:", self.api_key)
        
        self.test_conn_btn = QPushButton("Test Connection")
        self.lbl_test_result = QLabel("")
        test_layout = QHBoxLayout()
        test_layout.addWidget(self.test_conn_btn)
        test_layout.addWidget(self.lbl_test_result)
        main_lay.addRow("", test_layout)
        
        # --- Extractor Agent Settings ---
        ext_group = QGroupBox("Pre-Analyze Agent (Extractor)")
        ext_lay = QFormLayout(ext_group)
        
        self.ext_provider_cb = QComboBox()
        self.ext_provider_cb.addItems(["openai", "anthropic", "deepseek", "openrouter", "gemini", "local"])
        ext_lay.addRow("Provider:", self.ext_provider_cb)
        
        self.ext_model_name = QComboBox()
        self.ext_model_name.setEditable(True)
        ext_lay.addRow("Model Name:", self.ext_model_name)
        
        self.ext_api_key = QLineEdit()
        self.ext_api_key.setEchoMode(QLineEdit.Password)
        ext_lay.addRow("API Key:", self.ext_api_key)
        
        self.ext_infinite_retries = QCheckBox("Infinite Retries (Never Skip)")
        ext_lay.addRow("Behavior:", self.ext_infinite_retries)
        
        self.ext_chunk_size = QSpinBox()
        self.ext_chunk_size.setRange(10, 500)
        self.ext_chunk_size.setValue(75)
        ext_lay.addRow("Chunk Size (Lines):", self.ext_chunk_size)
        
        self.ext_test_conn_btn = QPushButton("Test Extractor Connection")
        ext_lay.addRow("", self.ext_test_conn_btn)
        
        # --- Project Paths Settings ---
        paths_group = QGroupBox("Project Paths & Config")
        paths_lay = QFormLayout(paths_group)
        
        self.path_glossary = QLineEdit()
        self.btn_browse_glossary = QPushButton("Browse")
        paths_lay.addRow("Glossary Path:", self._path_row(self.path_glossary, self.btn_browse_glossary))
        
        self.path_characters = QLineEdit()
        self.btn_browse_characters = QPushButton("Browse")
        paths_lay.addRow("Characters Path:", self._path_row(self.path_characters, self.btn_browse_characters))
        
        self.path_context = QLineEdit()
        self.btn_browse_context = QPushButton("Browse")
        paths_lay.addRow("Work Context Path:", self._path_row(self.path_context, self.btn_browse_context))
        
        self.path_output = QLineEdit()
        self.btn_browse_output = QPushButton("Browse")
        paths_lay.addRow("Output Folder:", self._path_row(self.path_output, self.btn_browse_output))
        
        self.constraint_mode = QComboBox()
        self.constraint_mode.addItems(["strict", "balanced", "off"])
        paths_lay.addRow("Constraint Mode:", self.constraint_mode)
        
        self.log_language_cb = QComboBox()
        self.log_language_cb.addItems(["Bilingual", "English", "Arabic"])
        paths_lay.addRow("Log Language:", self.log_language_cb)
        
        self.translation_style_cb = QComboBox()
        self.translation_style_cb.addItems(["Standard (فصحى)", "Colloquial (عامية)"])
        paths_lay.addRow("Translation Style:", self.translation_style_cb)
        
        self.max_retries = QSpinBox()
        self.max_retries.setRange(1, 10)
        
        self.infinite_retries_chk = QCheckBox("Infinite Retries (Never Skip)")
        
        retries_layout = QHBoxLayout()
        retries_layout.addWidget(self.max_retries)
        retries_layout.addWidget(self.infinite_retries_chk)
        paths_lay.addRow("Max Retries:", retries_layout)
        
        self.infinite_retries_chk.stateChanged.connect(lambda: self.max_retries.setEnabled(not self.infinite_retries_chk.isChecked()))
        
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 120)
        paths_lay.addRow("Timeout (sec):", self.timeout)
        
        self.force_single_line = QCheckBox("Force Single Line (No \\n)")
        paths_lay.addRow("Line Formatting:", self.force_single_line)
        
        
        layout.addWidget(main_group)
        layout.addWidget(ext_group)
        layout.addWidget(paths_group)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.reset_btn = QPushButton("Reset to Default")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.reset_btn)
        layout.addLayout(btn_layout)

    def _path_row(self, line_edit, btn):
        widget = QWidget()
        lay = QHBoxLayout(widget)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(line_edit)
        lay.addWidget(btn)
        return widget

class DataEditorTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        proj_lay = QHBoxLayout()
        proj_lay.addWidget(QLabel("Target Project:"))
        self.project_cb = QComboBox()
        self.project_cb.setEditable(True)
        self.project_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        proj_lay.addWidget(self.project_cb)
        layout.addLayout(proj_lay)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.char_tab = QWidget()
        char_lay = QVBoxLayout(self.char_tab)
        self.char_table = QTableWidget(0, 3)
        self.char_table.setHorizontalHeaderLabels(["Name", "Arabic Name", "Gender"])
        self.char_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.char_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        char_lay.addWidget(self.char_table)
        char_btns = QHBoxLayout()
        self.char_add = QPushButton("Add")
        self.char_del = QPushButton("Delete")
        self.char_save = QPushButton("Save")
        char_btns.addWidget(self.char_add)
        char_btns.addWidget(self.char_del)
        char_btns.addWidget(self.char_save)
        char_lay.addLayout(char_btns)
        self.tabs.addTab(self.char_tab, "Characters")
        
        self.context_tab = QWidget()
        ctx_lay = QVBoxLayout(self.context_tab)
        self.context_text = QTextEdit()
        ctx_lay.addWidget(self.context_text)
        self.context_save = QPushButton("Save")
        ctx_lay.addWidget(self.context_save)
        self.tabs.addTab(self.context_tab, "Work Context")
        
        self.glos_tab = QWidget()
        glos_lay = QVBoxLayout(self.glos_tab)
        self.glos_table = QTableWidget(0, 3)
        self.glos_table.setHorizontalHeaderLabels(["Term", "Translation", "Type"])
        self.glos_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.glos_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        glos_lay.addWidget(self.glos_table)
        glos_btns = QHBoxLayout()
        self.glos_add = QPushButton("Add")
        self.glos_del = QPushButton("Delete")
        self.glos_save = QPushButton("Save")
        glos_btns.addWidget(self.glos_add)
        glos_btns.addWidget(self.glos_del)
        glos_btns.addWidget(self.glos_save)
        glos_lay.addLayout(glos_btns)
        self.tabs.addTab(self.glos_tab, "Glossary")
        
        self.term_tab = QWidget()
        term_lay = QVBoxLayout(self.term_tab)
        self.term_table = QTableWidget(0, 4)
        self.term_table.setHorizontalHeaderLabels(["Term", "Translation", "Count", "Locked"])
        self.term_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.term_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        term_lay.addWidget(self.term_table)
        term_btns = QHBoxLayout()
        self.term_save = QPushButton("Save Changes")
        self.term_del = QPushButton("Delete Selected")
        term_btns.addWidget(self.term_save)
        term_btns.addWidget(self.term_del)
        term_lay.addLayout(term_btns)
        self.tabs.addTab(self.term_tab, "Term Memory")

class ReviewTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        top_lay = QHBoxLayout()
        top_lay.addWidget(QLabel("Anime:"))
        self.anime_cb = QComboBox()
        self.anime_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_lay.addWidget(self.anime_cb)
        
        top_lay.addWidget(QLabel("Episode:"))
        self.episode_cb = QComboBox()
        self.episode_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_lay.addWidget(self.episode_cb)
        
        self.refresh_btn = QPushButton("Refresh")
        top_lay.addWidget(self.refresh_btn)
        
        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["Show All", "Show Failed & Degraded Only"])
        top_lay.addWidget(self.filter_cb)
        layout.addLayout(top_lay)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Chunk", "ID", "English Text", "Arabic Translation", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.table)
        
        # Dedicated Edit Box
        edit_lay = QVBoxLayout()
        edit_lay.addWidget(QLabel("Edit Translation:"))
        self.edit_box = QTextEdit()
        self.edit_box.setMaximumHeight(80)
        # Set RTL direction for the edit box
        self.edit_box.setLayoutDirection(Qt.RightToLeft)
        edit_lay.addWidget(self.edit_box)
        layout.addLayout(edit_lay)
        
        bot_lay = QHBoxLayout()
        self.rebuild_btn = QPushButton("Save Edits & Rebuild Subtitles")
        bot_lay.addWidget(self.rebuild_btn)
        layout.addLayout(bot_lay)

class AnalyzeTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Config Section
        cfg_lay = QHBoxLayout()
        cfg_lay.addWidget(QLabel("Source Files:"))
        self.files_input = QLineEdit()
        self.files_input.setReadOnly(True)
        cfg_lay.addWidget(self.files_input)
        
        self.btn_browse = QPushButton("Browse Files...")
        cfg_lay.addWidget(self.btn_browse)
        
        self.btn_browse_folder = QPushButton("Browse Folder...")
        cfg_lay.addWidget(self.btn_browse_folder)
        
        cfg_lay.addWidget(QLabel("Language:"))
        self.lang_cb = QComboBox()
        self.lang_cb.addItems(["English", "Arabic"])
        cfg_lay.addWidget(self.lang_cb)
        layout.addLayout(cfg_lay)
        
        # Action Section
        act_lay = QHBoxLayout()
        act_lay.addWidget(QLabel("Target Project (Anime Name):"))
        self.project_cb = QComboBox()
        self.project_cb.setEditable(True)
        self.project_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        act_lay.addWidget(self.project_cb)
        
        self.btn_start = QPushButton("Start Auto-Extraction")
        self.btn_start.setStyleSheet("font-weight: bold; padding: 5px;")
        act_lay.addWidget(self.btn_start)
        layout.addLayout(act_lay)
        
        ctx_lay = QHBoxLayout()
        ctx_lay.addWidget(QLabel("Manual Work Context (Optional):"))
        self.work_context_input = QLineEdit()
        self.work_context_input.setPlaceholderText("e.g., A story about Saiyans... (Overrides project context if filled)")
        ctx_lay.addWidget(self.work_context_input)
        layout.addLayout(ctx_lay)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("Idle")
        layout.addWidget(self.lbl_status)
        
        # Log Console
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(80)
        self.log_console.setStyleSheet("background-color: #1e1e1e; color: #a9b7c6; font-family: Consolas;")
        layout.addWidget(self.log_console)
        
        # Results Section (Splitter or Tabs for Characters and Terms)
        self.results_tabs = QTabWidget()
        
        # Characters Tab
        self.char_tab = QWidget()
        char_lay = QVBoxLayout(self.char_tab)
        self.char_table = QTableWidget(0, 3)
        self.char_table.setHorizontalHeaderLabels(["Select", "Character Name", "Description / Role"])
        self.char_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.char_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        char_lay.addWidget(self.char_table)
        self.results_tabs.addTab(self.char_tab, "Extracted Characters")
        
        # Glossary Tab
        self.glos_tab = QWidget()
        glos_lay = QVBoxLayout(self.glos_tab)
        self.glos_table = QTableWidget(0, 4)
        self.glos_table.setHorizontalHeaderLabels(["Select", "Term", "Suggested Translation", "Type"])
        self.glos_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.glos_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        glos_lay.addWidget(self.glos_table)
        self.results_tabs.addTab(self.glos_tab, "Extracted Glossary Terms")
        
        layout.addWidget(self.results_tabs)
        
        # Save Section
        bot_lay = QHBoxLayout()
        self.btn_save = QPushButton("Save Selected to Project Data")
        self.btn_export = QPushButton("Export as Standalone JSON")
        bot_lay.addWidget(self.btn_save)
        bot_lay.addWidget(self.btn_export)
        layout.addLayout(bot_lay)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlorisSrt")
        self.setMinimumSize(900, 600)
        self.resize(1100, 750)
        
        # Set App Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.run_tab = RunTab()
        self.settings_tab = SettingsTab()
        self.data_editor_tab = DataEditorTab()
        self.review_tab = ReviewTab()
        self.analyze_tab = AnalyzeTab()
        
        self.tabs.addTab(self.run_tab, "Run")
        self.tabs.addTab(self.analyze_tab, "Pre-Analyze (Extraction)")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.data_editor_tab, "Data Editor")
        self.tabs.addTab(self.review_tab, "Review & Post-Edit")
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.lbl_status_left = QLabel("Ready")
        self.lbl_status_right = QLabel("Project: None")
        self.status_bar.addWidget(self.lbl_status_left, 1)
        self.status_bar.addPermanentWidget(self.lbl_status_right)
