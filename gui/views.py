from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, 
                             QLabel, QLineEdit, QProgressBar, QPlainTextEdit, 
                             QFormLayout, QComboBox, QSpinBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTextEdit, QCheckBox, 
                             QTabWidget, QMainWindow, QStatusBar, QAbstractItemView, QSizePolicy, QDialog, QDoubleSpinBox)
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
        
        project_label_layout = QHBoxLayout()
        project_label_layout.addWidget(QLabel("Project:"))
        self.project_cb = QComboBox()
        self.project_cb.setEditable(True)
        project_label_layout.addWidget(self.project_cb)
        
        self.lbl_episode = QLabel("Episode: None")
        
        project_layout = QHBoxLayout()
        
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel("<b>Detected / Selected Project</b>"))
        info_layout.addLayout(project_label_layout)
        info_layout.addWidget(self.lbl_episode)
        project_layout.addLayout(info_layout)
        
        prompt_layout = QVBoxLayout()
        prompt_mode_layout = QHBoxLayout()
        prompt_mode_layout.addWidget(QLabel("<b>System Prompt Mode:</b>"))
        self.prompt_mode_cb = QComboBox()
        self.prompt_mode_cb.addItems(["Default (agents.md/soul.md)", "Custom (User Input)"])
        prompt_mode_layout.addWidget(self.prompt_mode_cb)
        prompt_layout.addLayout(prompt_mode_layout)
        
        self.lbl_prompt_warning = QLabel("⚠️ You are overriding system behavior")
        self.lbl_prompt_warning.setStyleSheet("color: red; font-weight: bold;")
        self.lbl_prompt_warning.hide()
        prompt_layout.addWidget(self.lbl_prompt_warning)
        
        project_layout.addLayout(prompt_layout)
        layout.addLayout(project_layout)
        
        self.custom_prompt_group = QGroupBox("Custom Prompts")
        self.custom_prompt_group.hide()
        custom_layout = QVBoxLayout(self.custom_prompt_group)
        custom_layout.addWidget(QLabel("Custom AGENTS:"))
        self.custom_agents_edit = QTextEdit()
        self.custom_agents_edit.setMaximumHeight(100)
        custom_layout.addWidget(self.custom_agents_edit)
        custom_layout.addWidget(QLabel("Custom SOUL:"))
        self.custom_soul_edit = QTextEdit()
        self.custom_soul_edit.setMaximumHeight(100)
        custom_layout.addWidget(self.custom_soul_edit)
        
        self.save_custom_prompts_btn = QPushButton("Save Custom Prompts")
        self.save_custom_prompts_btn.setStyleSheet("padding: 5px;")
        custom_layout.addWidget(self.save_custom_prompts_btn)
        
        layout.addWidget(self.custom_prompt_group)
        
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
        self.translation_style_cb.addItems(["Standard (فصحى)", "Colloquial - White (عامية بيضاء)", "Colloquial - Egyptian (عامية مصرية)", "Colloquial - Saudi (عامية سعودية)"])
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
        self.glos_table = QTableWidget(0, 4)
        self.glos_table.setHorizontalHeaderLabels(["Term", "Translation", "Category", "Match Type"])
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
        top_lay.addWidget(QLabel("Project:"))
        self.project_cb = QComboBox()
        self.project_cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_lay.addWidget(self.project_cb)
        
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
        
        cfg_lay.addWidget(QLabel("Mode:"))
        self.mode_cb = QComboBox()
        self.mode_cb.addItems(["Balanced", "Characters Only", "Terms Only"])
        cfg_lay.addWidget(self.mode_cb)
        
        self.chk_translate = QCheckBox("Translate Result")
        self.chk_translate.setChecked(True)
        cfg_lay.addWidget(self.chk_translate)
        
        layout.addLayout(cfg_lay)
        
        # Action Section
        act_lay = QHBoxLayout()
        act_lay.addWidget(QLabel("Target Project (Project Name):"))
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
        self.char_table = QTableWidget(0, 4)
        self.char_table.setHorizontalHeaderLabels(["Select", "Character Name", "Arabic Name", "Description / Role"])
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

class QuickStartDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Start Workflow")
        self.resize(700, 500)
        
        layout = QVBoxLayout(self)
        
        text_view = QTextEdit()
        text_view.setReadOnly(True)
        
        html_content = """
        <h2>دليل المستخدم المبسط (Quick Start Workflow)</h2>
        <p>مرحباً بك في <b>FlorisSrt</b>! هذا الدليل السريع سيشرح لك أفضل خط سير عمل (Workflow) للحصول على أقصى جودة بأقل مجهود:</p>
        
        <h3>الخطوة الأولى: التهيئة والإعداد (Settings)</h3>
        <ol>
            <li>اذهب إلى نافذة <b>Settings</b>.</li>
            <li>اختر مزود الخدمة (مثلاً DeepSeek أو OpenAI) وأدخل <b>API Key</b> الخاص بك.</li>
            <li>اختر <b>Translation Style</b> (فصحى، عامية، الخ).</li>
            <li>اضغط <b>Save</b> ثم <b>Test Connection</b> للتأكد من أن اتصالك سليم.</li>
        </ol>

        <h3>الخطوة الثانية: استخراج البيانات والأسماء (Pre-Analyze) (اختياري لكنه مهم للأنمي)</h3>
        <ol>
            <li>اذهب إلى نافذة <b>Pre-Analyze (Extraction)</b>.</li>
            <li>اختر ملف أو مجلد الترجمة (SRT/ASS).</li>
            <li>اختر مسار مشروع جديد (مثال: projects/MyAnime).</li>
            <li>اضغط <b>Start Analysis</b>. <br><i>هذا سيجعل الذكاء الاصطناعي يقرأ الملف بالكامل ويستخرج أسماء الشخصيات والمصطلحات ليحفظها في المشروع، لضمان توحيد الأسماء في كل الحلقات.</i></li>
        </ol>

        <h3>الخطوة الثالثة: مراجعة الأسماء (Data Editor)</h3>
        <ol>
            <li>اذهب إلى نافذة <b>Data Editor</b> وافتح مشروعك.</li>
            <li>قم بمراجعة الشخصيات (Characters) والمصطلحات (Glossary).</li>
            <li>عدّل الترجمة المقترحة للأسماء إذا لم تعجبك، ثم اضغط <b>Save Data</b>.</li>
        </ol>

        <h3>الخطوة الرابعة: الترجمة الفعلية (Run)</h3>
        <ol>
            <li>اذهب إلى نافذة <b>Run</b>.</li>
            <li>قم بسحب وإفلات ملف الترجمة، وسيتم اكتشاف مشروعك تلقائياً إذا قمت بالخطوات السابقة.</li>
            <li>تأكد من اختيار <b>Default Mode</b> في الـ System Prompt (إلا إذا كنت تعرف ما تفعله).</li>
            <li>اضغط <b>Start</b> واترك النظام يترجم الحلقة بالكامل.</li>
        </ol>

        <h3>الخطوة الخامسة: المراجعة النهائية (Review & Post-Edit)</h3>
        <ol>
            <li>الآن وبعد انتهاء الترجمة، اذهب إلى <b>Review & Post-Edit</b>.</li>
            <li>افتح الملف المترجم (ستجده في مجلد episodes داخل مشروعك).</li>
            <li>قم بمراجعة الأسطر جنباً إلى جنب (عربي وإنجليزي). يمكنك تعديل أي خطأ هنا.</li>
            <li>اضغط <b>Save Export</b> للحصول على ملفك النهائي!</li>
        </ol>
        <hr>
        <p><i>💡 تلميح: لا تتردد في استخدام وضع الـ Custom Prompts إذا أردت توجيه الموديل بأسلوب معين للترجمة!</i></p>
        """
        text_view.setHtml(html_content)
        layout.addWidget(text_view)
        
        btn_close = QPushButton("Got it! إغلاق")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

class UsageTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        
        # Left Panel (Pricing)
        left_panel = QWidget()
        left_lay = QVBoxLayout(left_panel)
        left_lay.addWidget(QLabel("<b>Pricing Engine</b>"))
        
        left_lay.addWidget(QLabel("Provider:"))
        self.provider_input = QComboBox()
        self.provider_input.setEditable(True)
        self.provider_input.addItems(["openai", "anthropic", "deepseek", "openrouter", "gemini", "local"])
        left_lay.addWidget(self.provider_input)
        
        left_lay.addWidget(QLabel("Model:"))
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        left_lay.addWidget(self.model_input)
        
        left_lay.addWidget(QLabel("Input / 1M tokens ($):"))
        self.price_in = QDoubleSpinBox()
        self.price_in.setRange(0, 1000)
        self.price_in.setDecimals(4)
        left_lay.addWidget(self.price_in)
        
        left_lay.addWidget(QLabel("Output / 1M tokens ($):"))
        self.price_out = QDoubleSpinBox()
        self.price_out.setRange(0, 1000)
        self.price_out.setDecimals(4)
        left_lay.addWidget(self.price_out)
        
        self.save_pricing_btn = QPushButton("Save Pricing")
        left_lay.addWidget(self.save_pricing_btn)
        
        left_lay.addWidget(QLabel("<br><i>Select provider/model<br>to view or set prices.</i>"))
        
        left_lay.addStretch()
        layout.addWidget(left_panel, 1)
        
        # Right Panel (Ledger Table & Summary)
        right_panel = QWidget()
        right_lay = QVBoxLayout(right_panel)
        
        # Filters
        filter_lay = QHBoxLayout()
        filter_lay.addWidget(QLabel("Project:"))
        self.filter_project = QComboBox()
        self.filter_project.setEditable(True)
        self.filter_project.setMinimumWidth(150)
        self.filter_project.addItem("All")
        filter_lay.addWidget(self.filter_project)
        
        filter_lay.addWidget(QLabel("Model:"))
        self.filter_model = QComboBox()
        self.filter_model.setEditable(True)
        self.filter_model.setMinimumWidth(200)
        self.filter_model.addItem("All")
        filter_lay.addWidget(self.filter_model)
        
        filter_lay.addStretch()
        right_lay.addLayout(filter_lay)
        
        # Summary Header
        sum_lay = QHBoxLayout()
        self.lbl_total_tokens = QLabel("Total Tokens: <b>0</b>")
        self.lbl_total_cost = QLabel("Total Cost: <b>$0.00</b>")
        self.lbl_run_cost = QLabel("This Run: <b>$0.00</b>")
        
        self.lbl_total_tokens.setStyleSheet("font-size: 14px;")
        self.lbl_total_cost.setStyleSheet("font-size: 14px; color: #4CAF50;")
        self.lbl_run_cost.setStyleSheet("font-size: 14px; color: #2196F3; font-weight: bold;")
        
        sum_lay.addWidget(self.lbl_total_tokens)
        sum_lay.addWidget(QLabel(" | "))
        sum_lay.addWidget(self.lbl_total_cost)
        sum_lay.addWidget(QLabel(" | "))
        sum_lay.addWidget(self.lbl_run_cost)
        sum_lay.addStretch()
        
        self.btn_refresh = QPushButton("Refresh")
        self.btn_export = QPushButton("Export CSV")
        self.btn_clear = QPushButton("Clear Ledger")
        self.btn_clear.setStyleSheet("color: #ff4c4c;")
        sum_lay.addWidget(self.btn_refresh)
        sum_lay.addWidget(self.btn_export)
        sum_lay.addWidget(self.btn_clear)
        right_lay.addLayout(sum_lay)
        
        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Project", "Episode", "Model", "In", "Out", "Cost", "Est."])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 100) # Project
        self.table.setColumnWidth(1, 80)  # Episode
        self.table.setColumnWidth(2, 250) # Model
        self.table.setColumnWidth(3, 60)  # In
        self.table.setColumnWidth(4, 60)  # Out
        self.table.setColumnWidth(5, 80)  # Cost
        self.table.setColumnWidth(6, 60)  # Est.
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        right_lay.addWidget(self.table)
        
        layout.addWidget(right_panel, 3)

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
        
        # Menu Bar
        menu_bar = self.menuBar()
        help_menu = menu_bar.addMenu("Help")
        self.action_quick_start = help_menu.addAction("Quick Start")
        
        self.run_tab = RunTab()
        self.analyze_tab = AnalyzeTab()
        self.data_editor_tab = DataEditorTab()
        self.review_tab = ReviewTab()
        self.usage_tab = UsageTab()
        self.settings_tab = SettingsTab()
        
        self.tabs.addTab(self.run_tab, "Run")
        self.tabs.addTab(self.analyze_tab, "Pre-Analyze (Extraction)")
        self.tabs.addTab(self.data_editor_tab, "Data Editor")
        self.tabs.addTab(self.review_tab, "Review & Post-Edit")
        self.tabs.addTab(self.usage_tab, "Cost & Usage")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.lbl_status_left = QLabel("Ready")
        self.lbl_status_right = QLabel("Project: None")
        self.status_bar.addWidget(self.lbl_status_left, 1)
        self.status_bar.addPermanentWidget(self.lbl_status_right)
