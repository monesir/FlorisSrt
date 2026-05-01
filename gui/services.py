import os
import json
import re
from PySide6.QtCore import QObject, Signal, QProcess, QProcessEnvironment
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.project_resolution import ProjectResolution

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ProjectService:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.join(PROJECT_ROOT, "projects")
        self.resolver = ProjectResolution(self.base_dir)

    def resolve_project(self, input_path: str, force_anime_name=None) -> tuple[str, str]:
        info = self.resolver.resolve_project(input_path, force_anime_name=force_anime_name)
        return info["anime"], info["episode"]

    def project_exists(self, anime: str) -> bool:
        return os.path.exists(os.path.join(self.base_dir, anime, "data"))

    def bootstrap_project(self, anime: str, input_path: str) -> None:
        data_dir = os.path.join(self.base_dir, anime, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        defaults = {
            "glossary.json": {"terms": []},
            "characters.json": {"characters": []},
            "work_context.json": {"description": ""},
            "term_memory.json": {}
        }
        
        for file_name, content in defaults.items():
            path = os.path.join(data_dir, file_name)
            if not os.path.exists(path):
                self._atomic_write(path, content)

    def load_project_data(self, anime: str, file_name: str) -> dict:
        path = os.path.join(self.base_dir, anime, "data", file_name)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_project_data(self, anime: str, file_name: str, data: dict):
        dir_path = os.path.join(self.base_dir, anime, "data")
        os.makedirs(dir_path, exist_ok=True)
        path = os.path.join(dir_path, file_name)
        self._atomic_write(path, data)

    def _atomic_write(self, path: str, data: dict):
        temp_path = path + ".tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)

class ConfigService:
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join(PROJECT_ROOT, "config", "user_settings.json")

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return self.get_defaults()

    def save(self, data):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        temp_path = self.config_path + ".tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, self.config_path)

    def get_defaults(self):
        return {
            "model": {"provider": "openai", "name": "gpt-4o", "api_key": ""},
            "paths": {"glossary": "", "characters": "", "work_context": ""},
            "output": {"folder": ""},
            "execution": {"constraint_mode": "balanced", "max_retries": 5, "timeout": 30},
            "preferences": {"log_language": "Bilingual", "translation_style": "Standard (فصحى)"}
        }

class RunnerService(QObject):
    log_ready = Signal(str)
    state_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.handle_finished)
        self.process.errorOccurred.connect(self.handle_error)

    def start(self, file_path, provider="openai", api_key="", model_name="", resume=False, project_name=None, log_language="Bilingual", translation_style="Standard (فصحى)"):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
            
        self.state_changed.emit("Running")
        pipeline_path = os.path.join(PROJECT_ROOT, "pipeline.py")
        self.process.setWorkingDirectory(PROJECT_ROOT)
        
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(env)
        
        args = ["--input", file_path, "--provider", provider, "--api-key", api_key]
        if model_name:
            args.extend(["--model-name", model_name])
        if project_name:
            args.extend(["--project-name", project_name])
        if log_language:
            args.extend(["--log-language", log_language])
        if translation_style:
            args.extend(["--translation-style", translation_style])
        if resume:
            args.append("--resume")
            
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle
            self.process.start(sys.executable, ["--pipeline"] + args)
        else:
            # Running from source
            self.process.start(sys.executable, ["-u", pipeline_path] + args)

    def stop(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished(1000)
            self.state_changed.emit("Idle")

    def handle_stdout(self):
        text = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.log_ready.emit(text)

    def handle_stderr(self):
        text = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.log_ready.emit(f"ERROR: {text}")

    def handle_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.state_changed.emit("Completed")
        else:
            self.state_changed.emit("Failed")

    def handle_error(self, error):
        self.state_changed.emit("Failed")
        self.log_ready.emit(f"Process Error: {error}")
