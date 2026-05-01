import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import urllib.request
import urllib.error
from datetime import datetime
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QTableWidgetItem, QComboBox, QCheckBox, QWidget, QHBoxLayout
from PySide6.QtCore import QTimer, Qt, QProcess, QThread, Signal
from views import MainWindow
from services import ProjectService, ConfigService, RunnerService
from core.state_manager import StateManager
from parsers.rebuilder import Rebuilder

class ConnectionTester(QThread):
    result_ready = Signal(str, bool)

    def __init__(self, provider, api_key):
        super().__init__()
        self.provider = provider
        self.api_key = api_key

    def run(self):
        if not self.api_key and self.provider != "local":
            self.result_ready.emit("Failed: No API Key", False)
            return
        try:
            headers = {"User-Agent": "AnimeTranslator/1.0"}
            url = ""
            if self.provider == "openai":
                url = "https://api.openai.com/v1/models"
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.provider == "anthropic":
                url = "https://api.anthropic.com/v1/messages"
                headers["x-api-key"] = self.api_key
                headers["anthropic-version"] = "2023-06-01"
            elif self.provider == "deepseek":
                url = "https://api.deepseek.com/models"
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.provider == "openrouter":
                url = "https://openrouter.ai/api/v1/auth/key"
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            else:
                self.result_ready.emit("Local/Unknown Provider", True)
                return
            
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        self.result_ready.emit("Connected", True)
            except urllib.error.HTTPError as e:
                if e.code in [401, 403]:
                    self.result_ready.emit("Failed: Invalid API Key", False)
                elif self.provider == "anthropic" and e.code == 400:
                    self.result_ready.emit("Connected", True)
                else:
                    self.result_ready.emit(f"Failed: HTTP {e.code}", False)
            except urllib.error.URLError:
                self.result_ready.emit("Failed: Network Error", False)
        except Exception:
            self.result_ready.emit("Failed: Exception", False)

from PySide6.QtCore import Signal

class ExtractorWorker(QThread):
    progress_updated = Signal(int, int)
    finished_extraction = Signal(dict)
    error_occurred = Signal(str)
    log_updated = Signal(str)

    def __init__(self, cfg, file_paths, source_lang, work_context="", mode="Balanced", translate_result=True):
        super().__init__()
        self.cfg = cfg
        self.file_paths = file_paths
        self.source_lang = source_lang
        self.work_context = work_context
        self.mode = mode
        self.translate_result = translate_result

    def run(self):
        try:
            from core.extractor import ExtractorEngine
            
            ext_cfg = self.cfg.get("extractor_agent", {})
            provider = ext_cfg.get("provider", self.cfg.get("provider", "openai"))
            api_key = ext_cfg.get("api_key", self.cfg.get("api_key", ""))
            model = ext_cfg.get("model", self.cfg.get("model", ""))
            infinite = ext_cfg.get("infinite_retries", False)
            
            engine = ExtractorEngine(
                provider=provider,
                api_key=api_key,
                model=model,
                infinite_retries=infinite
            )
            
            merged_result = {"characters": [], "terms": [], "total_tokens": 0}
            total_files = len(self.file_paths)
            
            for f_idx, fp in enumerate(self.file_paths):
                def prog_cb(c_idx, c_total):
                    base = (f_idx / total_files) * 100
                    chunk_prog = (c_idx / c_total) * (100 / total_files)
                    self.progress_updated.emit(int(base + chunk_prog), 100)
                    
                def log_cb(msg):
                    self.log_updated.emit(msg)
                    
                chunk_size = ext_cfg.get("chunk_size", 75)
                res = engine.process_file(fp, self.source_lang, self.work_context, prog_cb, log_cb, chunk_size=chunk_size, mode=self.mode, translate_result=self.translate_result)
                
                merged_result["characters"].extend(res.get("characters", []))
                merged_result["terms"].extend(res.get("terms", []))
                merged_result["total_tokens"] += res.get("total_tokens", 0)
                
            self.progress_updated.emit(100, 100)
            self.log_updated.emit(f"\n============================\nExtraction completed!\nTotal tokens used (All files): {merged_result['total_tokens']}\n============================")
            self.finished_extraction.emit(merged_result)
        except Exception as e:
            self.error_occurred.emit(str(e))

class AppController:
    def __init__(self, window: MainWindow):
        self.window = window
        self.project_service = ProjectService()
        self.config_service = ConfigService()
        self.runner = RunnerService()
        
        self.current_anime = None
        self.current_episode = None
        
        self.config_cache = self.config_service.load()
        if "providers" not in self.config_cache:
            self.config_cache["providers"] = {}
            if "model" in self.config_cache:
                old_prov = self.config_cache["model"].get("provider", "openai")
                self.config_cache["providers"][old_prov] = {
                    "name": self.config_cache["model"].get("name", ""),
                    "api_key": self.config_cache["model"].get("api_key", "")
                }
        
        self._setup_connections()
        self._load_config()
        
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self._poll_progress)
        self.log_timer.start(1000)

    def _setup_connections(self):
        self.window.run_tab.browse_btn.clicked.connect(self._browse_file)
        self.window.run_tab.browse_folder_btn.clicked.connect(self._browse_folder)
        self.window.run_tab.file_input.textChanged.connect(self._on_file_selected)
        self.window.run_tab.start_btn.clicked.connect(self._start_translation)
        self.window.run_tab.resume_btn.clicked.connect(self._resume_translation)
        self.window.run_tab.stop_btn.clicked.connect(self._stop_translation)
        self.window.run_tab.open_out_btn.clicked.connect(self._open_output_folder)
        
        self.runner.log_ready.connect(self._append_log)
        self.runner.state_changed.connect(self._on_runner_state_changed)
        
        self.batch_queue = []
        self.total_batch = 0
        
        self.current_anime = None
        self.window.settings_tab.save_btn.clicked.connect(self._save_config)
        self.window.settings_tab.reset_btn.clicked.connect(self._reset_config)
        self.window.settings_tab.test_conn_btn.clicked.connect(self._test_connection)
        self.window.settings_tab.ext_test_conn_btn.clicked.connect(self._test_ext_connection)
        
        self.window.settings_tab.provider_cb.currentTextChanged.connect(self._on_provider_changed)
        self.window.settings_tab.ext_provider_cb.currentTextChanged.connect(self._on_ext_provider_changed)
        self.window.settings_tab.api_key.textEdited.connect(self._cache_provider_data)
        self.window.settings_tab.model_name.editTextChanged.connect(self._cache_provider_data)
        self.window.settings_tab.ext_api_key.textEdited.connect(self._cache_ext_provider_data)
        self.window.settings_tab.ext_model_name.editTextChanged.connect(self._cache_ext_provider_data)
        
        self.window.settings_tab.btn_browse_glossary.clicked.connect(lambda: self._browse_settings_file(self.window.settings_tab.path_glossary, "JSON Files (*.json)"))
        self.window.settings_tab.btn_browse_characters.clicked.connect(lambda: self._browse_settings_file(self.window.settings_tab.path_characters, "JSON Files (*.json)"))
        self.window.settings_tab.btn_browse_context.clicked.connect(lambda: self._browse_settings_file(self.window.settings_tab.path_context, "JSON Files (*.json)"))
        self.window.settings_tab.btn_browse_output.clicked.connect(lambda: self._browse_settings_dir(self.window.settings_tab.path_output))
        
        self.window.data_editor_tab.project_cb.currentTextChanged.connect(self._on_data_editor_project_changed)
        self.window.data_editor_tab.char_add.clicked.connect(self._add_character_row)
        self.window.data_editor_tab.char_del.clicked.connect(lambda: self._delete_table_row(self.window.data_editor_tab.char_table))
        self.window.data_editor_tab.char_save.clicked.connect(self._save_characters)

        self.window.data_editor_tab.glos_add.clicked.connect(self._add_glossary_row)
        self.window.data_editor_tab.glos_del.clicked.connect(lambda: self._delete_table_row(self.window.data_editor_tab.glos_table))
        self.window.data_editor_tab.glos_save.clicked.connect(self._save_glossary)

        self.window.data_editor_tab.context_save.clicked.connect(self._save_work_context)

        self.window.data_editor_tab.term_del.clicked.connect(lambda: self._delete_table_row(self.window.data_editor_tab.term_table))
        self.window.data_editor_tab.term_save.clicked.connect(self._save_term_memory)
        
        self.window.review_tab.refresh_btn.clicked.connect(self._refresh_review_projects)
        self.window.review_tab.anime_cb.currentTextChanged.connect(self._on_review_anime_changed)
        self.window.review_tab.episode_cb.currentTextChanged.connect(self._load_review_data)
        self.window.review_tab.filter_cb.currentTextChanged.connect(self._load_review_data)
        self.window.review_tab.rebuild_btn.clicked.connect(self._save_and_rebuild_subtitles)
        self.window.review_tab.table.itemSelectionChanged.connect(self._on_review_row_selected)
        self.window.review_tab.edit_box.textChanged.connect(self._on_review_edit_box_changed)
        
        self.window.analyze_tab.btn_browse.clicked.connect(self._on_analyze_browse)
        self.window.analyze_tab.btn_browse_folder.clicked.connect(self._on_analyze_browse_folder)
        self.window.analyze_tab.btn_start.clicked.connect(self._on_analyze_start)
        self.window.analyze_tab.btn_save.clicked.connect(self._on_analyze_save)
        self.window.analyze_tab.btn_export.clicked.connect(self._on_analyze_export)
        
        self.window.tabs.currentChanged.connect(self._on_tab_changed)

    def _append_log(self, text):
        self.window.run_tab.logs_view.appendPlainText(text)

    def _log_internal(self, en_msg, ar_msg):
        lang = self.window.settings_tab.log_language_cb.currentText()
        time_str = f"[{datetime.now().strftime('%H:%M:%S')}] "
        if lang == "English":
            self.window.run_tab.logs_view.appendPlainText(f"{time_str}{en_msg}")
        elif lang == "Arabic":
            self.window.run_tab.logs_view.appendPlainText(f"{time_str}{ar_msg}")
        else:
            self.window.run_tab.logs_view.appendPlainText(f"{time_str}{en_msg} | {ar_msg}")

    def _on_tab_changed(self, index):
        current_widget = self.window.tabs.currentWidget()
        if current_widget == self.window.data_editor_tab:
            self._refresh_editor_projects()
        elif current_widget == self.window.review_tab:
            if getattr(self, 'is_running', False):
                QMessageBox.warning(self.window, "Running", "Cannot review while translation is running.")
                self.window.tabs.setCurrentIndex(0)
                return
            self._refresh_review_projects()
        elif current_widget == self.window.analyze_tab:
            self._refresh_analyze_projects()

    # --- Pre-Analyze Dropdown Refresh ---
    def _refresh_analyze_projects(self):
        projects_tree = self.project_service.get_projects_tree()
        cb = self.window.analyze_tab.project_cb
        current = cb.currentText()
        cb.blockSignals(True)
        cb.clear()
        cb.addItem("")
        cb.addItems(list(projects_tree.keys()))
        if current in projects_tree:
            cb.setCurrentText(current)
        cb.blockSignals(False)
        
    # --- Data Editor Dropdown Refresh ---
    def _refresh_editor_projects(self):
        projects_tree = self.project_service.get_projects_tree()
        cb = self.window.data_editor_tab.project_cb
        current = self.current_anime or cb.currentText()
        cb.blockSignals(True)
        cb.clear()
        cb.addItem("")
        cb.addItems(list(projects_tree.keys()))
        if current in projects_tree:
            cb.setCurrentText(current)
        cb.blockSignals(False)
        self._load_project_data_to_editor()
        
    def _on_data_editor_project_changed(self, new_project):
        new_project = new_project.strip()
        self.current_anime = new_project if new_project else None
        
        if new_project and not self.project_service.project_exists(new_project):
            self.project_service.bootstrap_project(new_project, "")
            
        self._load_project_data_to_editor()

    # --- Review Tab Methods ---
    def _refresh_review_projects(self):
        self.projects_tree = self.project_service.get_projects_tree()
        
        cb = self.window.review_tab.anime_cb
        cb.blockSignals(True)
        cb.clear()
        cb.addItems(list(self.projects_tree.keys()))
        cb.blockSignals(False)
        
        if self.projects_tree:
            self._on_review_anime_changed(cb.currentText())
            
    def _on_review_anime_changed(self, anime_name):
        if not hasattr(self, 'projects_tree'): return
        episodes = self.projects_tree.get(anime_name, [])
        
        cb = self.window.review_tab.episode_cb
        cb.blockSignals(True)
        cb.clear()
        cb.addItems(episodes)
        cb.blockSignals(False)
        
        if episodes:
            self._load_review_data()

    def _load_review_data(self):
        anime = self.window.review_tab.anime_cb.currentText()
        episode = self.window.review_tab.episode_cb.currentText()
        if not anime or not episode: return
        ep_dir = os.path.join(self.project_service.base_dir, anime, 'episodes', episode)
        
        self.current_review_state_manager = StateManager(ep_dir)
        state = self.current_review_state_manager.load_or_create_state(0)
        total_chunks = state.get('total_chunks', 0)
        
        all_segments = self.current_review_state_manager.load_all_chunks(total_chunks)
        self.current_review_segments = all_segments
        
        self._populate_review_table(all_segments)
        
    def _populate_review_table(self, segments):
        table = self.window.review_tab.table
        filter_type = self.window.review_tab.filter_cb.currentText()
        
        table.blockSignals(True)
        table.setRowCount(0)
        
        for seg in segments:
            is_failed = (seg.get('text', '') == seg.get('translated', '')) or not seg.get('translated', '')
            
            if filter_type == "Show Failed & Degraded Only" and not is_failed:
                continue
                
            row = table.rowCount()
            table.insertRow(row)
            
            chunk_item = QTableWidgetItem(str(seg.get('chunk_index', '')))
            chunk_item.setFlags(chunk_item.flags() & ~Qt.ItemIsEditable)
            
            id_item = QTableWidgetItem(str(seg.get('id', '')))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            
            en_item = QTableWidgetItem(seg.get('text', ''))
            en_item.setFlags(en_item.flags() & ~Qt.ItemIsEditable)
            
            ar_item = QTableWidgetItem(seg.get('translated', ''))
            ar_item.setData(Qt.UserRole, seg) # Store full segment data
            
            status_text = "Failed" if is_failed else "OK"
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            if is_failed:
                status_item.setForeground(Qt.red)
                ar_item.setBackground(Qt.red)
                ar_item.setForeground(Qt.white)
            else:
                status_item.setForeground(Qt.green)
                
            table.setItem(row, 0, chunk_item)
            table.setItem(row, 1, id_item)
            table.setItem(row, 2, en_item)
            table.setItem(row, 3, ar_item)
            table.setItem(row, 4, status_item)
            
        table.blockSignals(False)
        self.window.review_tab.edit_box.clear()
        self.current_review_row = -1

    def _on_review_row_selected(self):
        table = self.window.review_tab.table
        selected_items = table.selectedItems()
        if not selected_items:
            self.current_review_row = -1
            self.window.review_tab.edit_box.clear()
            return
            
        row = selected_items[0].row()
        self.current_review_row = row
        ar_item = table.item(row, 3)
        if ar_item:
            self.window.review_tab.edit_box.blockSignals(True)
            self.window.review_tab.edit_box.setPlainText(ar_item.text())
            self.window.review_tab.edit_box.blockSignals(False)

    def _on_review_edit_box_changed(self):
        if not hasattr(self, 'current_review_row') or self.current_review_row == -1:
            return
            
        table = self.window.review_tab.table
        row = self.current_review_row
        ar_item = table.item(row, 3)
        if ar_item:
            new_text = self.window.review_tab.edit_box.toPlainText()
            ar_item.setText(new_text)
            
            seg_data = ar_item.data(Qt.UserRole)
            if seg_data:
                seg_data['translated'] = new_text
                ar_item.setData(Qt.UserRole, seg_data)
                
            ar_item.setBackground(Qt.white)
            ar_item.setForeground(Qt.black)
            
            status_item = table.item(row, 4)
            if status_item:
                status_item.setText("OK (Edited)")
                status_item.setForeground(Qt.blue)

    def _save_and_rebuild_subtitles(self):
        if not hasattr(self, 'current_review_state_manager'): return
        
        table = self.window.review_tab.table
        updated_segments = []
        for row in range(table.rowCount()):
            ar_item = table.item(row, 3)
            if ar_item:
                seg_data = ar_item.data(Qt.UserRole)
                if seg_data:
                    updated_segments.append(seg_data)
        
        self.current_review_state_manager.save_segments_to_chunks(updated_segments)
        
        state = self.current_review_state_manager.load_or_create_state(0)
        input_file = state.get('input_file')
        format_type = state.get('format_type', 'srt')
        
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self.window, "Warning", "Original input file not found or not set in project state. Please locate it to copy subtitle headers.")
            input_file, _ = QFileDialog.getOpenFileName(self.window, "Select Original Subtitle File", "", "Subtitles (*.ass *.srt)")
            if not input_file:
                return
        
        output_file, _ = QFileDialog.getSaveFileName(self.window, "Save Rebuilt Subtitle", "", "Subtitles (*.ass *.srt)")
        if not output_file:
            return
            
        try:
            rebuilder = Rebuilder()
            all_segments = self.current_review_state_manager.load_all_chunks(state.get('total_chunks', 0))
            if format_type == 'ass':
                rebuilder.build_ass(all_segments, input_file, output_file)
            else:
                rebuilder.build_srt(all_segments, output_file)
                
            QMessageBox.information(self.window, "Success", "Subtitle file rebuilt successfully with your manual edits!")
        except Exception as e:
            QMessageBox.critical(self.window, "Error", f"Failed to rebuild subtitle: {str(e)}")

    def _browse_settings_file(self, line_edit, filter_ext):
        path, _ = QFileDialog.getOpenFileName(self.window, "Select File", "", filter_ext)
        if path:
            line_edit.setText(path)

    def _browse_settings_dir(self, line_edit):
        path = QFileDialog.getExistingDirectory(self.window, "Select Output Directory")
        if path:
            line_edit.setText(path)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self.window, "Select Subtitle", "", "Subtitles (*.srt *.ass)")
        if path:
            self.batch_project_name = None
            self.batch_queue = [path]
            self.total_batch = 1
            self.window.run_tab.lbl_batch.setText("Batch Queue: 1/1")
            self.window.run_tab.file_input.setText(path)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self.window, "Select Folder")
        if not folder: return
        
        self.batch_project_name = os.path.basename(folder)
        target_ext = self.window.run_tab.batch_format_cb.currentText()
        files = []
        skipped_count = 0
        for root, _, filenames in os.walk(folder):
            for f in filenames:
                if f.lower().endswith(target_ext) or (target_ext == "Both" and f.lower().endswith(('.srt', '.ass'))):
                    file_path = os.path.join(root, f)
                    
                    # Check if already translated
                    anime, episode = self.project_service.resolve_project(file_path, force_anime_name=self.batch_project_name)
                    base_name = os.path.splitext(f)[0]
                    ext = os.path.splitext(f)[1]
                    output_path = os.path.join(self.project_service.base_dir, anime, "episodes", episode, f"{base_name}_floris{ext}")
                    
                    if os.path.exists(output_path):
                        skipped_count += 1
                        continue # Skip completed file
                        
                    files.append(file_path)
                    
        if not files:
            if skipped_count > 0:
                reply = QMessageBox.question(
                    self.window, 
                    "All Files Translated", 
                    f"Found {skipped_count} files, but they are already translated.\nDo you want to re-translate them (overwrite)?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    for root, _, filenames in os.walk(folder):
                        for f in filenames:
                            if f.lower().endswith(target_ext) or (target_ext == "Both" and f.lower().endswith(('.srt', '.ass'))):
                                files.append(os.path.join(root, f))
                else:
                    return
            else:
                QMessageBox.warning(self.window, "No Files", f"No {target_ext} files found in the selected folder.")
                return
            
        files.sort()
        self.batch_queue = files
        self.total_batch = len(files)
        self.window.run_tab.lbl_batch.setText(f"Batch Queue: 1/{self.total_batch}")
        
        # Load the first file
        self.window.run_tab.file_input.setText(self.batch_queue[0])

    def _on_file_selected(self, path):
        if not path or not os.path.exists(path): return
        anime, episode = self.project_service.resolve_project(path, force_anime_name=getattr(self, 'batch_project_name', None))
        
        if not self.project_service.project_exists(anime):
            self.project_service.bootstrap_project(anime, path)
            msg = QMessageBox(self.window)
            msg.setWindowTitle("Project Created")
            msg.setText(f"Project '{anime}' created successfully.\nBasic data initialized.")
            btn_open = msg.addButton("Open Data Editor", QMessageBox.AcceptRole)
            msg.addButton("Continue", QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() == btn_open:
                self.window.tabs.setCurrentIndex(2)

        self.current_anime = anime
        self.current_episode = episode
        
        self.window.run_tab.lbl_anime.setText(f"Anime: {anime}")
        self.window.run_tab.lbl_episode.setText(f"Episode: {episode}")
        self.window.lbl_status_right.setText(f"Project: {anime}")
        
        self.window.run_tab.start_btn.setEnabled(True)
        self.window.run_tab.open_out_btn.setEnabled(True)
        state_path = os.path.join(self.project_service.base_dir, anime, "episodes", episode, "project.json")
        self.window.run_tab.resume_btn.setEnabled(os.path.exists(state_path))
        
        self.window.data_editor_tab.setEnabled(True)
        cb = self.window.data_editor_tab.project_cb
        cb.blockSignals(True)
        if cb.findText(anime) == -1:
            cb.addItem(anime)
        cb.setCurrentText(anime)
        cb.blockSignals(False)
        
        self._load_project_data_to_editor()

    def _load_project_data_to_editor(self):
        if not self.current_anime:
            self.window.data_editor_tab.char_table.setRowCount(0)
            self.window.data_editor_tab.glos_table.setRowCount(0)
            self.window.data_editor_tab.context_text.clear()
            self.window.data_editor_tab.term_table.setRowCount(0)
            return
        
        char_data = self.project_service.load_project_data(self.current_anime, "characters.json")
        chars = char_data.get("characters", [])
        self.window.data_editor_tab.char_table.setRowCount(0)
        for c in chars:
            self._add_character_row(c.get("name", ""), c.get("arabic_name", ""), c.get("gender", "unknown"))
            
        glos_data = self.project_service.load_project_data(self.current_anime, "glossary.json")
        terms = glos_data.get("terms", [])
        self.window.data_editor_tab.glos_table.setRowCount(0)
        for t in terms:
            typ = t.get("type", "hard")
            cat = t.get("category", "")
            if typ not in ["hard", "soft"]:
                cat = typ
                typ = t.get("match_type", "hard")
            self._add_glossary_row(t.get("term", ""), t.get("translation", ""), cat, typ)
            
        ctx_data = self.project_service.load_project_data(self.current_anime, "work_context.json")
        self.window.data_editor_tab.context_text.setText(ctx_data.get("description", ""))
        
        term_data = self.project_service.load_project_data(self.current_anime, "term_memory.json")
        self.window.data_editor_tab.term_table.setRowCount(0)
        for term, data in term_data.items():
            self._add_term_memory_row(term, data.get("translation", ""), data.get("count", 0), data.get("locked", False))

    def _add_character_row(self, name="", arabic_name="", gender="unknown"):
        table = self.window.data_editor_tab.char_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(name))
        table.setItem(row, 1, QTableWidgetItem(arabic_name))
        cb = QComboBox()
        cb.addItems(["male", "female", "unknown"])
        cb.setCurrentText(gender)
        table.setCellWidget(row, 2, cb)

    def _add_glossary_row(self, term="", trans="", category="", match_type="hard"):
        table = self.window.data_editor_tab.glos_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(term))
        table.setItem(row, 1, QTableWidgetItem(trans))
        table.setItem(row, 2, QTableWidgetItem(category))
        cb = QComboBox()
        cb.addItems(["hard", "soft"])
        cb.setCurrentText(match_type)
        table.setCellWidget(row, 3, cb)

    def _add_term_memory_row(self, term, trans, count, locked):
        table = self.window.data_editor_tab.term_table
        row = table.rowCount()
        table.insertRow(row)
        
        it_term = QTableWidgetItem(term)
        it_term.setFlags(it_term.flags() & ~Qt.ItemIsEditable)
        table.setItem(row, 0, it_term)
        
        table.setItem(row, 1, QTableWidgetItem(trans))
        
        it_count = QTableWidgetItem(str(count))
        it_count.setFlags(it_count.flags() & ~Qt.ItemIsEditable)
        table.setItem(row, 2, it_count)
        
        chk_widget = QWidget()
        chk_lay = QHBoxLayout(chk_widget)
        chk_lay.setContentsMargins(0,0,0,0)
        chk_lay.setAlignment(Qt.AlignCenter)
        chk = QCheckBox()
        chk.setChecked(locked)
        chk_lay.addWidget(chk)
        table.setCellWidget(row, 3, chk_widget)
        if locked:
            it_term.setFont(it_term.font().setBold(True))

    def _delete_table_row(self, table):
        rows = set(item.row() for item in table.selectedItems())
        for row in sorted(rows, reverse=True):
            table.removeRow(row)

    def _save_characters(self):
        if not self.current_anime:
            QMessageBox.warning(self.window, "Warning", "Please select or create a Target Project first.")
            return
        table = self.window.data_editor_tab.char_table
        chars = []
        for i in range(table.rowCount()):
            name = table.item(i, 0).text().strip()
            arabic_item = table.item(i, 1)
            arabic_name = arabic_item.text().strip() if arabic_item else ""
            gender = table.cellWidget(i, 2).currentText()
            if name:
                char_obj = {"name": name, "gender": gender}
                if arabic_name:
                    char_obj["arabic_name"] = arabic_name
                chars.append(char_obj)
        self.project_service.save_project_data(self.current_anime, "characters.json", {"characters": chars})
        QMessageBox.information(self.window, "Saved", "Characters saved.")

    def _save_glossary(self):
        if not self.current_anime:
            QMessageBox.warning(self.window, "Warning", "Please select or create a Target Project first.")
            return
        table = self.window.data_editor_tab.glos_table
        terms = []
        for i in range(table.rowCount()):
            term = table.item(i, 0).text().strip()
            trans = table.item(i, 1).text().strip()
            cat_item = table.item(i, 2)
            category = cat_item.text().strip() if cat_item else ""
            m_type = table.cellWidget(i, 3).currentText()
            if term:
                terms.append({"term": term, "translation": trans, "category": category, "type": m_type})
        self.project_service.save_project_data(self.current_anime, "glossary.json", {"terms": terms})
        QMessageBox.information(self.window, "Saved", "Glossary saved.")

    def _save_work_context(self):
        if not self.current_anime:
            QMessageBox.warning(self.window, "Warning", "Please select or create a Target Project first.")
            return
        desc = self.window.data_editor_tab.context_text.toPlainText()
        self.project_service.save_project_data(self.current_anime, "work_context.json", {"description": desc})
        QMessageBox.information(self.window, "Saved", "Work context saved.")

    def _save_term_memory(self):
        if not self.current_anime:
            QMessageBox.warning(self.window, "Warning", "Please select or create a Target Project first.")
            return
        table = self.window.data_editor_tab.term_table
        data = {}
        for i in range(table.rowCount()):
            term = table.item(i, 0).text().strip()
            trans = table.item(i, 1).text().strip()
            count = int(table.item(i, 2).text().strip() or "0")
            chk = table.cellWidget(i, 3).findChild(QCheckBox)
            locked = chk.isChecked() if chk else False
            if term:
                data[term] = {"translation": trans, "count": count, "locked": locked}
        self.project_service.save_project_data(self.current_anime, "term_memory.json", data)
        QMessageBox.information(self.window, "Saved", "Term Memory saved.")

    def _on_provider_changed(self, new_provider):
        prov_data = self.config_cache.get("providers", {}).get(new_provider, {})
        
        models = {
            "gemini": [
                "gemini-3.1-flash-lite-preview",
                "gemini-3.1-pro-preview",
                "gemini-2.5-pro",
                "gemini-2.5-flash-lite"
            ],
            "openrouter": [
                "minimax/minimax-m2.5:free",
                "tencent/hy3-preview:free",
                "google/gemma-4-26b-a4b-it:free",
                "google/gemma-4-31b-it:free",
                "nvidia/nemotron-3-super-120b-a12b:free",
                "qwen/qwen3.6-plus",
                "deepseek/deepseek-v3.2"
            ],
            "deepseek": [
                "deepseek-v4-pro",
                "deepseek-v4-flash",
                "deepseek-chat"
            ],
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4.5-preview"],
            "anthropic": ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            "local": ["local-model"]
        }
        
        # Update combobox items without triggering editTextChanged
        self.window.settings_tab.model_name.blockSignals(True)
        self.window.settings_tab.model_name.clear()
        if new_provider in models:
            self.window.settings_tab.model_name.addItems(models[new_provider])
        
        if not prov_data.get("name"):
            prov_data["name"] = models.get(new_provider, [""])[0]
            
        self.window.settings_tab.model_name.setCurrentText(prov_data.get("name", ""))
        self.window.settings_tab.model_name.blockSignals(False)
        
        self.window.settings_tab.api_key.blockSignals(True)
        self.window.settings_tab.api_key.setText(prov_data.get("api_key", ""))
        self.window.settings_tab.api_key.blockSignals(False)
        
    def _on_ext_provider_changed(self, new_provider):
        prov_data = self.config_cache.get("ext_providers", {}).get(new_provider, {})
        
        models = {
            "gemini": [
                "gemini-3.1-flash-lite-preview",
                "gemini-3.1-pro-preview",
                "gemini-2.5-pro",
                "gemini-2.5-flash-lite"
            ],
            "openrouter": [
                "minimax/minimax-m2.5:free",
                "tencent/hy3-preview:free",
                "google/gemma-4-26b-a4b-it:free",
                "google/gemma-4-31b-it:free",
                "nvidia/nemotron-3-super-120b-a12b:free",
                "qwen/qwen3.6-plus",
                "deepseek/deepseek-v3.2"
            ],
            "deepseek": [
                "deepseek-v4-pro",
                "deepseek-v4-flash",
                "deepseek-chat"
            ],
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4.5-preview"],
            "anthropic": ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            "local": ["local-model"]
        }
        
        self.window.settings_tab.ext_model_name.blockSignals(True)
        self.window.settings_tab.ext_model_name.clear()
        if new_provider in models:
            self.window.settings_tab.ext_model_name.addItems(models[new_provider])
        
        if not prov_data.get("name"):
            prov_data["name"] = models.get(new_provider, [""])[0]
            
        self.window.settings_tab.ext_model_name.setCurrentText(prov_data.get("name", ""))
        self.window.settings_tab.ext_model_name.blockSignals(False)
        
        self.window.settings_tab.ext_api_key.blockSignals(True)
        self.window.settings_tab.ext_api_key.setText(prov_data.get("api_key", ""))
        self.window.settings_tab.ext_api_key.blockSignals(False)

    def _cache_provider_data(self):
        st = self.window.settings_tab
        current_prov = st.provider_cb.currentText()
        if "providers" not in self.config_cache:
            self.config_cache["providers"] = {}
        self.config_cache["providers"][current_prov] = {
            "name": st.model_name.currentText().strip(),
            "api_key": st.api_key.text().strip()
        }

    def _cache_ext_provider_data(self):
        st = self.window.settings_tab
        current_prov = st.ext_provider_cb.currentText()
        if "ext_providers" not in self.config_cache:
            self.config_cache["ext_providers"] = {}
        self.config_cache["ext_providers"][current_prov] = {
            "name": st.ext_model_name.currentText().strip(),
            "api_key": st.ext_api_key.text().strip()
        }

    def _load_config(self):
        config = self.config_cache
        st = self.window.settings_tab
        model = config.get("model", {})
        st.provider_cb.setCurrentText(model.get("provider", "openai"))
        self._on_provider_changed(model.get("provider", "openai"))
        
        ext_agent = config.get("extractor_agent", {})
        
        # Migrate old single-key config to new ext_providers structure if needed
        if "ext_providers" not in config:
            config["ext_providers"] = {}
            if "provider" in ext_agent:
                config["ext_providers"][ext_agent["provider"]] = {
                    "name": ext_agent.get("model", ""),
                    "api_key": ext_agent.get("api_key", "")
                }
                
        st.ext_provider_cb.setCurrentText(ext_agent.get("provider", "openai"))
        self._on_ext_provider_changed(ext_agent.get("provider", "openai"))
        
        st.ext_infinite_retries.setChecked(ext_agent.get("infinite_retries", False))
        st.ext_chunk_size.setValue(ext_agent.get("chunk_size", 75))
        
        paths = config.get("paths", {})
        st.path_glossary.setText(paths.get("glossary", ""))
        st.path_characters.setText(paths.get("characters", ""))
        st.path_context.setText(paths.get("work_context", ""))
        st.path_output.setText(config.get("output", {}).get("folder", ""))
        
        exe = config.get("execution", {})
        st.constraint_mode.setCurrentText(exe.get("constraint_mode", "balanced"))
        st.max_retries.setValue(exe.get("max_retries", 5))
        st.timeout.setValue(exe.get("timeout", 30))
        if "infinite_retries" in exe:
            st.infinite_retries_chk.setChecked(exe.get("infinite_retries", False))
        
        prefs = config.get("preferences", {})
        st.log_language_cb.setCurrentText(prefs.get("log_language", "Bilingual"))
        st.translation_style_cb.setCurrentText(prefs.get("translation_style", "Standard (فصحى)"))
        st.force_single_line.setChecked(prefs.get("force_single_line", False))

    def _save_config(self, show_msg=True):
        self._cache_provider_data()
        self._cache_ext_provider_data()
        st = self.window.settings_tab
        
        if "model" not in self.config_cache:
            self.config_cache["model"] = {}
        self.config_cache["model"]["provider"] = st.provider_cb.currentText()
        
        self.config_cache["paths"] = {
            "glossary": st.path_glossary.text(),
            "characters": st.path_characters.text(),
            "work_context": st.path_context.text()
        }
        
        self.config_cache["extractor_agent"] = {
            "provider": st.ext_provider_cb.currentText(),
            "model": st.ext_model_name.currentText().strip(),
            "api_key": st.ext_api_key.text().strip(),
            "infinite_retries": st.ext_infinite_retries.isChecked(),
            "chunk_size": st.ext_chunk_size.value()
        }
        
        self.config_cache["output"] = {"folder": st.path_output.text()}
        self.config_cache["execution"] = {
            "constraint_mode": st.constraint_mode.currentText(),
            "max_retries": st.max_retries.value(),
            "timeout": st.timeout.value(),
            "infinite_retries": st.infinite_retries_chk.isChecked()
        }
        
        self.config_cache["preferences"] = {
            "log_language": st.log_language_cb.currentText(),
            "translation_style": st.translation_style_cb.currentText(),
            "force_single_line": st.force_single_line.isChecked()
        }
        
        self.config_service.save(self.config_cache)
        if show_msg:
            QMessageBox.information(self.window, "Saved", "Settings saved.")

    def _reset_config(self):
        self.config_service.save(self.config_service.get_defaults())
        self._load_config()

    def _test_connection(self):
        provider = self.window.settings_tab.provider_cb.currentText()
        api_key = self.window.settings_tab.api_key.text().strip()
        self.window.settings_tab.lbl_test_result.setText("Testing...")
        self.window.settings_tab.lbl_test_result.setStyleSheet("color: orange; font-weight: bold;")
        
        self.tester = ConnectionTester(provider, api_key)
        self.tester.result_ready.connect(lambda msg, success: self._update_test_result(msg, success, self.window.settings_tab.lbl_test_result))
        self.tester.start()
        
    def _test_ext_connection(self):
        provider = self.window.settings_tab.ext_provider_cb.currentText()
        api_key = self.window.settings_tab.ext_api_key.text().strip()
        self.window.settings_tab.lbl_test_result.setText("Testing Extractor...")
        self.window.settings_tab.lbl_test_result.setStyleSheet("color: orange; font-weight: bold;")
        
        self.tester = ConnectionTester(provider, api_key)
        self.tester.result_ready.connect(lambda msg, success: self._update_test_result(msg, success, self.window.settings_tab.lbl_test_result))
        self.tester.start()

    def _update_test_result(self, msg, success, label_widget):
        label_widget.setText(msg)
        color = "green" if success else "red"
        label_widget.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _start_translation(self):
        path = self.window.run_tab.file_input.text()
        if not path: return
        self._set_ui_running_state(True)
        self._save_config(show_msg=False) # Save config before start
        
        provider = self.window.settings_tab.provider_cb.currentText()
        api_key = self.window.settings_tab.api_key.text().strip()
        model_name = self.window.settings_tab.model_name.currentText().strip()
        log_lang = self.config_cache.get("preferences", {}).get("log_language", "Bilingual")
        trans_style = self.config_cache.get("preferences", {}).get("translation_style", "Standard (فصحى)")
        force_single = self.config_cache.get("preferences", {}).get("force_single_line", False)
        
        timeout_val = self.config_cache.get("execution", {}).get("timeout", 120)
        max_retries_val = self.config_cache.get("execution", {}).get("max_retries", 3)
        infinite_retries_val = self.config_cache.get("execution", {}).get("infinite_retries", False)
        
        self.runner.start(
            file_path=path,
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            resume=False,
            project_name=getattr(self, 'batch_project_name', None),
            log_language=log_lang,
            translation_style=trans_style,
            force_single_line=force_single,
            timeout=timeout_val,
            max_retries=max_retries_val,
            infinite_retries=infinite_retries_val
        )

    def _resume_translation(self):
        path = self.window.run_tab.file_input.text()
        if not path: return
        self._set_ui_running_state(True)
        self._save_config(show_msg=False)
        
        provider = self.window.settings_tab.provider_cb.currentText()
        api_key = self.window.settings_tab.api_key.text().strip()
        model_name = self.window.settings_tab.model_name.currentText().strip()
        log_lang = self.config_cache.get("preferences", {}).get("log_language", "Bilingual")
        trans_style = self.config_cache.get("preferences", {}).get("translation_style", "Standard (فصحى)")
        force_single = self.config_cache.get("preferences", {}).get("force_single_line", False)
        
        timeout_val = self.config_cache.get("execution", {}).get("timeout", 120)
        max_retries_val = self.config_cache.get("execution", {}).get("max_retries", 3)
        infinite_retries_val = self.config_cache.get("execution", {}).get("infinite_retries", False)
        
        self._log_internal("Resuming translation...", "جاري استئناف الترجمة...")
        self.runner.start(
            file_path=path,
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            resume=True,
            project_name=getattr(self, 'batch_project_name', None),
            log_language=log_lang,
            translation_style=trans_style,
            force_single_line=force_single,
            timeout=timeout_val,
            max_retries=max_retries_val,
            infinite_retries=infinite_retries_val
        )

    def _stop_translation(self):
        self._log_internal("Translation stopped forcefully.", "تم إيقاف عملية الترجمة إجبارياً.")
        self.is_stopping = True
        self.runner.stop()

    def _on_runner_state_changed(self, state):
        self.window.lbl_status_left.setText(state)
        self.window.run_tab.lbl_status.setText(f"Status: {state}")
        if state in ["Idle", "Completed", "Failed"]:
            self._set_ui_running_state(False)
            self.window.run_tab.stop_btn.setEnabled(False)
            self._load_project_data_to_editor()
            self._poll_progress(force=True)
            
            intentional_stop = getattr(self, 'is_stopping', False)
            if intentional_stop:
                self.is_stopping = False
            
            # Batch Queue Processing
            if hasattr(self, 'batch_queue') and self.batch_queue and (state == "Completed" or state == "Failed"):
                if intentional_stop:
                    self.batch_queue = []
                    self.window.run_tab.lbl_batch.setText("Batch Queue: Idle")
                    return
                    
                current_file = self.window.run_tab.file_input.text()
                if current_file in self.batch_queue:
                    self.batch_queue.remove(current_file)
                    
                if self.batch_queue:
                    idx = self.total_batch - len(self.batch_queue) + 1
                    self.window.run_tab.lbl_batch.setText(f"Batch Queue: {idx}/{self.total_batch}")
                    next_file = self.batch_queue[0]
                    self.window.run_tab.file_input.setText(next_file)
                    self._log_internal("\nAuto-advancing to next file in queue...\n", "\nالانتقال التلقائي للملف التالي في الطابور...\n")
                    # Delay start slightly to allow UI refresh
                    QTimer.singleShot(1000, self._start_translation)
                    return
            
            if state == "Completed":
                QMessageBox.information(self.window, "Finished", "Translation finished")
                self.window.data_editor_tab.setEnabled(True)
            elif state == "Failed" and not intentional_stop:
                if not hasattr(self, 'batch_queue') or not self.batch_queue:
                    QMessageBox.warning(self.window, "Error", "Chunk failed after retries")

    def _set_ui_running_state(self, running):
        self.window.settings_tab.setEnabled(not running)
        self.window.data_editor_tab.setEnabled(not running)
        self.window.run_tab.browse_btn.setEnabled(not running)
        self.window.run_tab.start_btn.setEnabled(not running)
        self.window.run_tab.resume_btn.setEnabled(not running)
        self.window.run_tab.stop_btn.setEnabled(running)

    def _open_output_folder(self):
        if not self.current_anime or not self.current_episode: return
        ep_path = os.path.join(self.project_service.base_dir, self.current_anime, "episodes", self.current_episode)
        if os.path.exists(ep_path):
            os.startfile(ep_path)

    def _poll_progress(self, force=False):
        if not force and self.runner.process.state() != QProcess.ProcessState.Running:
            return
            
        if self.current_anime and self.current_episode:
            log_path = os.path.join(self.project_service.base_dir, self.current_anime, "episodes", self.current_episode, "project.json")
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                        tot = state.get("total_chunks", 0)
                        cur = len(set(state.get("completed_chunks", []) + state.get("failed_chunks", []) + state.get("degraded_chunks", [])))
                        if tot > 0:
                            self.window.run_tab.progress_bar.setValue(int((cur/tot)*100))
                            self.window.run_tab.lbl_chunk.setText(f"Chunk: {cur}/{tot}")
                except Exception:
                    pass

    # --- Pre-Analyze Tab Methods ---
    def _on_analyze_browse(self):
        paths, _ = QFileDialog.getOpenFileNames(self.window, "Select Subtitle Files", "", "Subtitle Files (*.ass *.srt)")
        if paths:
            self.window.analyze_tab.files_input.setText(";".join(paths))
            self.window.analyze_tab.files_input.setCursorPosition(0)
            self.window.analyze_tab.log_console.append(f"Loaded {len(paths)} file(s) for analysis.")
            
    def _on_analyze_browse_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self.window, "Select Folder Containing Subtitles")
        if dir_path:
            import glob
            files = glob.glob(os.path.join(dir_path, "**", "*.ass"), recursive=True) + \
                    glob.glob(os.path.join(dir_path, "**", "*.srt"), recursive=True)
            if files:
                self.window.analyze_tab.files_input.setText(";".join(files))
                self.window.analyze_tab.files_input.setCursorPosition(0)
                self.window.analyze_tab.log_console.append(f"Loaded {len(files)} file(s) from folder for analysis.")
            else:
                QMessageBox.information(self.window, "No Files", "No .ass or .srt files found in the selected folder.")

    def _on_analyze_start(self):
        files_str = self.window.analyze_tab.files_input.text()
        if not files_str:
            QMessageBox.warning(self.window, "Warning", "Please select files to analyze.")
            return
            
        file_paths = files_str.split(";")
        lang = self.window.analyze_tab.lang_cb.currentText()
        
        self.window.analyze_tab.btn_start.setEnabled(False)
        self.window.analyze_tab.lbl_status.setText("Status: Analyzing... This may take a while depending on file size.")
        self.window.analyze_tab.char_table.setRowCount(0)
        self.window.analyze_tab.glos_table.setRowCount(0)
        self.window.analyze_tab.progress_bar.setValue(0)
        self.window.analyze_tab.log_console.clear()
        
        project = self.window.analyze_tab.project_cb.currentText().strip()
        work_context = ""
        if project:
            ctx_data = self.project_service.load_project_data(project, "work_context.json")
            work_context = ctx_data.get("description", "")
            
        manual_ctx = self.window.analyze_tab.work_context_input.text().strip()
        if manual_ctx:
            work_context = manual_ctx
        
        mode = self.window.analyze_tab.mode_cb.currentText()
        translate_result = self.window.analyze_tab.chk_translate.isChecked()
        
        self.ext_worker = ExtractorWorker(self.config_cache, file_paths, lang, work_context, mode, translate_result)
        self.ext_worker.progress_updated.connect(lambda v, m: self.window.analyze_tab.progress_bar.setValue(v))
        self.ext_worker.log_updated.connect(lambda msg: self.window.analyze_tab.log_console.append(msg))
        self.ext_worker.finished_extraction.connect(self._on_analyze_finished)
        self.ext_worker.error_occurred.connect(self._on_analyze_error)
        self.ext_worker.start()

    def _on_analyze_finished(self, result):
        self.window.analyze_tab.btn_start.setEnabled(True)
        self.window.analyze_tab.lbl_status.setText("Status: Analysis complete!")
        self.window.analyze_tab.progress_bar.setValue(100)
        
        # Populate Characters
        chars = result.get("characters", [])
        ctable = self.window.analyze_tab.char_table
        ctable.setRowCount(len(chars))
        for r, char in enumerate(chars):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked)
            ctable.setItem(r, 0, chk)
            ctable.setItem(r, 1, QTableWidgetItem(char.get('name', '')))
            ctable.setItem(r, 2, QTableWidgetItem(char.get('arabic_name', '')))
            ctable.setItem(r, 3, QTableWidgetItem(char.get('description', '')))
            
        # Populate Terms
        terms = result.get("terms", [])
        gtable = self.window.analyze_tab.glos_table
        gtable.setRowCount(len(terms))
        for r, term in enumerate(terms):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked)
            gtable.setItem(r, 0, chk)
            gtable.setItem(r, 1, QTableWidgetItem(term.get('term', '')))
            gtable.setItem(r, 2, QTableWidgetItem(term.get('translation_suggestion', '')))
            gtable.setItem(r, 3, QTableWidgetItem(term.get('type', '')))

    def _on_analyze_error(self, err_msg):
        self.window.analyze_tab.btn_start.setEnabled(True)
        self.window.analyze_tab.lbl_status.setText("Status: Error")
        QMessageBox.critical(self.window, "Error", f"Analysis failed: {err_msg}")

    def _on_analyze_save(self):
        project = self.window.analyze_tab.project_cb.currentText().strip()
        if not project:
            QMessageBox.warning(self.window, "Warning", "Please specify a Target Project (Anime Name).")
            return
            
        self.project_service.bootstrap_project(project, "")
        
        # Load existing data
        char_data = self.project_service.load_project_data(project, "characters.json")
        glos_data = self.project_service.load_project_data(project, "glossary.json")
        
        existing_chars = char_data.get("characters", [])
        existing_terms = glos_data.get("terms", [])
        
        existing_char_names = {c.get("name", "").lower() for c in existing_chars}
        existing_term_names = {t.get("term", "").lower() for t in existing_terms}
        
        # Collect Characters
        ctable = self.window.analyze_tab.char_table
        added_count = 0
        for r in range(ctable.rowCount()):
            if ctable.item(r, 0).checkState() == Qt.Checked:
                name = ctable.item(r, 1).text().strip()
                arabic_name = ctable.item(r, 2).text().strip()
                desc = ctable.item(r, 3).text().strip()
                if name and name.lower() not in existing_char_names:
                    existing_chars.append({"name": name, "arabic_name": arabic_name, "gender": "unknown", "description": desc})
                    existing_char_names.add(name.lower())
                    added_count += 1
                    
        # Collect Terms
        gtable = self.window.analyze_tab.glos_table
        for r in range(gtable.rowCount()):
            if gtable.item(r, 0).checkState() == Qt.Checked:
                term = gtable.item(r, 1).text().strip()
                trans = gtable.item(r, 2).text().strip()
                typ = gtable.item(r, 3).text().strip()
                if term and term.lower() not in existing_term_names:
                    existing_terms.append({"term": term, "translation": trans, "category": typ, "type": "hard"})
                    existing_term_names.add(term.lower())
                    added_count += 1
                    
        if added_count == 0:
            QMessageBox.information(self.window, "Info", "No new items were selected or all selected items already exist in the project.")
            return
            
        # Save back
        self.project_service.save_project_data(project, "characters.json", {"characters": existing_chars})
        self.project_service.save_project_data(project, "glossary.json", {"terms": existing_terms})
            
        QMessageBox.information(self.window, "Saved", f"{added_count} new item(s) saved to project '{project}' successfully!")
        self._refresh_data_editor() # Refresh UI

    def _on_analyze_export(self):
        # Collect Characters
        new_chars = []
        ctable = self.window.analyze_tab.char_table
        for r in range(ctable.rowCount()):
            if ctable.item(r, 0).checkState() == Qt.Checked:
                name = ctable.item(r, 1).text().strip()
                arabic_name = ctable.item(r, 2).text().strip()
                desc = ctable.item(r, 3).text().strip()
                if name:
                    new_chars.append({"name": name, "arabic_name": arabic_name, "gender": "unknown", "description": desc})
                    
        # Collect Terms
        new_terms = []
        gtable = self.window.analyze_tab.glos_table
        for r in range(gtable.rowCount()):
            if gtable.item(r, 0).checkState() == Qt.Checked:
                term = gtable.item(r, 1).text().strip()
                trans = gtable.item(r, 2).text().strip()
                typ = gtable.item(r, 3).text().strip()
                if term:
                    new_terms.append({"term": term, "translation": trans, "category": typ, "type": "hard"})
                    
        dir_path = QFileDialog.getExistingDirectory(self.window, "Select Export Folder")
        if dir_path:
            import json
            try:
                char_file = os.path.join(dir_path, 'characters.json')
                glos_file = os.path.join(dir_path, 'glossary.json')
                
                with open(char_file, 'w', encoding='utf-8') as f:
                    json.dump({"characters": new_chars}, f, ensure_ascii=False, indent=2)
                    
                with open(glos_file, 'w', encoding='utf-8') as f:
                    json.dump({"terms": new_terms}, f, ensure_ascii=False, indent=2)
                    
                QMessageBox.information(self.window, "Exported", f"Data exported successfully to:\n{dir_path}")
            except Exception as e:
                QMessageBox.critical(self.window, "Error", f"Failed to export: {e}")

if __name__ == "__main__":
    import ctypes
    import os
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--pipeline":
        # PyInstaller subprocess mode
        sys.argv.pop(1) # Remove --pipeline so pipeline.py argparse works
        
        # Add root dir to path so imports work
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if getattr(sys, 'frozen', False):
            root_dir = sys._MEIPASS
        sys.path.insert(0, root_dir)
        
        import pipeline
        pipeline.main()
        sys.exit(0)

    if os.name == 'nt':
        myappid = 'monesir.florissrt.app.1' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
    app = QApplication(sys.argv)
    window = MainWindow()
    controller = AppController(window)
    window.show()
    sys.exit(app.exec())
