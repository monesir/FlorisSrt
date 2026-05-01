import sys
import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QTableWidgetItem, QComboBox, QCheckBox, QWidget, QHBoxLayout
from PySide6.QtCore import QTimer, Qt, QProcess, QThread, Signal
from views import MainWindow
from services import ProjectService, ConfigService, RunnerService

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
        
        self.window.settings_tab.provider_cb.currentTextChanged.connect(self._on_provider_changed)
        self.window.settings_tab.api_key.textEdited.connect(self._cache_provider_data)
        self.window.settings_tab.model_name.editTextChanged.connect(self._cache_provider_data)
        
        self.window.settings_tab.btn_browse_glossary.clicked.connect(lambda: self._browse_settings_file(self.window.settings_tab.path_glossary, "JSON Files (*.json)"))
        self.window.settings_tab.btn_browse_characters.clicked.connect(lambda: self._browse_settings_file(self.window.settings_tab.path_characters, "JSON Files (*.json)"))
        self.window.settings_tab.btn_browse_context.clicked.connect(lambda: self._browse_settings_file(self.window.settings_tab.path_context, "JSON Files (*.json)"))
        self.window.settings_tab.btn_browse_output.clicked.connect(lambda: self._browse_settings_dir(self.window.settings_tab.path_output))
        
        self.window.data_editor_tab.char_add.clicked.connect(self._add_character_row)
        self.window.data_editor_tab.char_del.clicked.connect(lambda: self._delete_table_row(self.window.data_editor_tab.char_table))
        self.window.data_editor_tab.char_save.clicked.connect(self._save_characters)

        self.window.data_editor_tab.glos_add.clicked.connect(self._add_glossary_row)
        self.window.data_editor_tab.glos_del.clicked.connect(lambda: self._delete_table_row(self.window.data_editor_tab.glos_table))
        self.window.data_editor_tab.glos_save.clicked.connect(self._save_glossary)

        self.window.data_editor_tab.context_save.clicked.connect(self._save_work_context)

        self.window.data_editor_tab.term_del.clicked.connect(lambda: self._delete_table_row(self.window.data_editor_tab.term_table))
        self.window.data_editor_tab.term_save.clicked.connect(self._save_term_memory)
        
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
        if index == 2:
            self._load_project_data_to_editor()

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
                        continue # Skip completed file
                        
                    files.append(file_path)
                    
        if not files:
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
        self.window.data_editor_tab.lbl_project.setText(f"Editing Project: {anime}")
        
        self._load_project_data_to_editor()

    def _load_project_data_to_editor(self):
        if not self.current_anime: return
        
        char_data = self.project_service.load_project_data(self.current_anime, "characters.json")
        chars = char_data.get("characters", [])
        self.window.data_editor_tab.char_table.setRowCount(0)
        for c in chars:
            self._add_character_row(c.get("name", ""), c.get("gender", "unknown"))
            
        glos_data = self.project_service.load_project_data(self.current_anime, "glossary.json")
        terms = glos_data.get("terms", [])
        self.window.data_editor_tab.glos_table.setRowCount(0)
        for t in terms:
            self._add_glossary_row(t.get("term", ""), t.get("translation", ""), t.get("type", "hard"))
            
        ctx_data = self.project_service.load_project_data(self.current_anime, "work_context.json")
        self.window.data_editor_tab.context_text.setText(ctx_data.get("description", ""))
        
        term_data = self.project_service.load_project_data(self.current_anime, "term_memory.json")
        self.window.data_editor_tab.term_table.setRowCount(0)
        for term, data in term_data.items():
            self._add_term_memory_row(term, data.get("translation", ""), data.get("count", 0), data.get("locked", False))

    def _add_character_row(self, name="", gender="unknown"):
        table = self.window.data_editor_tab.char_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(name))
        cb = QComboBox()
        cb.addItems(["male", "female", "unknown"])
        cb.setCurrentText(gender)
        table.setCellWidget(row, 1, cb)

    def _add_glossary_row(self, term="", trans="", type="hard"):
        table = self.window.data_editor_tab.glos_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(term))
        table.setItem(row, 1, QTableWidgetItem(trans))
        cb = QComboBox()
        cb.addItems(["hard", "soft"])
        cb.setCurrentText(type)
        table.setCellWidget(row, 2, cb)

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
        table = self.window.data_editor_tab.char_table
        chars = []
        for i in range(table.rowCount()):
            name = table.item(i, 0).text().strip()
            gender = table.cellWidget(i, 1).currentText()
            if name:
                chars.append({"name": name, "gender": gender})
        self.project_service.save_project_data(self.current_anime, "characters.json", {"characters": chars})
        QMessageBox.information(self.window, "Saved", "Characters saved.")

    def _save_glossary(self):
        table = self.window.data_editor_tab.glos_table
        terms = []
        for i in range(table.rowCount()):
            term = table.item(i, 0).text().strip()
            trans = table.item(i, 1).text().strip()
            ttype = table.cellWidget(i, 2).currentText()
            if term:
                terms.append({"term": term, "translation": trans, "type": ttype})
        self.project_service.save_project_data(self.current_anime, "glossary.json", {"terms": terms})
        QMessageBox.information(self.window, "Saved", "Glossary saved.")

    def _save_work_context(self):
        desc = self.window.data_editor_tab.context_text.toPlainText()
        self.project_service.save_project_data(self.current_anime, "work_context.json", {"description": desc})
        QMessageBox.information(self.window, "Saved", "Work context saved.")

    def _save_term_memory(self):
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
                    self.window.settings_tab.translation_style_cb.setCurrentText(prefs.get("translation_style", "Standard (فصحى)"))
            self.window.settings_tab.force_single_line.setChecked(prefs.get("force_single_line", False))
        self.window.settings_tab.model_name.blockSignals(False)
        
        self.window.settings_tab.api_key.blockSignals(True)
        self.window.settings_tab.api_key.setText(prov_data.get("api_key", ""))
        self.window.settings_tab.api_key.blockSignals(False)

    def _cache_provider_data(self):
        st = self.window.settings_tab
        current_prov = st.provider_cb.currentText()
        if "providers" not in self.config_cache:
            self.config_cache["providers"] = {}
        self.config_cache["providers"][current_prov] = {
            "name": st.model_name.currentText().strip(),
            "api_key": st.api_key.text().strip()
        }

    def _load_config(self):
        config = self.config_cache
        st = self.window.settings_tab
        model = config.get("model", {})
        st.provider_cb.setCurrentText(model.get("provider", "openai"))
        self._on_provider_changed(model.get("provider", "openai"))
        
        paths = config.get("paths", {})
        st.path_glossary.setText(paths.get("glossary", ""))
        st.path_characters.setText(paths.get("characters", ""))
        st.path_context.setText(paths.get("work_context", ""))
        st.path_output.setText(config.get("output", {}).get("folder", ""))
        
        exe = config.get("execution", {})
        st.constraint_mode.setCurrentText(exe.get("constraint_mode", "balanced"))
        st.max_retries.setValue(exe.get("max_retries", 5))
        st.timeout.setValue(exe.get("timeout", 30))
        st.log_language_cb.setCurrentText(exe.get("log_language", "Bilingual"))

    def _save_config(self, show_msg=True):
        self._cache_provider_data()
        st = self.window.settings_tab
        
        if "model" not in self.config_cache:
            self.config_cache["model"] = {}
        self.config_cache["model"]["provider"] = st.provider_cb.currentText()
        
        self.config_cache["paths"] = {
            "glossary": st.path_glossary.text(),
            "characters": st.path_characters.text(),
            "work_context": st.path_context.text()
        }
        self.config_cache["output"] = {"folder": st.path_output.text()}
        self.config_cache["execution"] = {
            "constraint_mode": st.constraint_mode.currentText(),
            "max_retries": st.max_retries.value(),
            "timeout": st.timeout.value()
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
        self.tester.result_ready.connect(self._update_test_result)
        self.tester.start()

    def _update_test_result(self, msg, success):
        self.window.settings_tab.lbl_test_result.setText(msg)
        color = "green" if success else "red"
        self.window.settings_tab.lbl_test_result.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _start_translation(self):
        path = self.window.run_tab.file_input.text()
        if not path: return
        self._set_ui_running_state(True)
        self._save_config(show_msg=False) # Save config before start
        
        provider = self.window.settings_tab.provider_cb.currentText()
        api_key = self.window.settings_tab.api_key.text().strip()
        model_name = self.window.settings_tab.model_name.currentText().strip()
        log_lang = config.get("preferences", {}).get("log_language", "Bilingual")
        trans_style = config.get("preferences", {}).get("translation_style", "Standard (فصحى)")
        force_single = config.get("preferences", {}).get("force_single_line", False)
        
        self.runner.start(
            file_path=file_path,
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            resume=False,
            project_name=None,
            log_language=log_lang,
            translation_style=trans_style,
            force_single_line=force_single
        )

    def _resume_translation(self):
        path = self.window.run_tab.file_input.text()
        if not path: return
        self._set_ui_running_state(True)
        self._save_config(show_msg=False)
        
        provider = self.window.settings_tab.provider_cb.currentText()
        api_key = self.window.settings_tab.api_key.text().strip()
        model_name = self.window.settings_tab.model_name.currentText().strip()
        log_lang = self.window.settings_tab.log_language_cb.currentText()
        
        self._log_internal("Resuming translation...", "جاري استئناف الترجمة...")
        self.runner.start(path, provider=provider, api_key=api_key, model_name=model_name, resume=True, project_name=getattr(self, 'batch_project_name', None), log_language=log_lang)

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
