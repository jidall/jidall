from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QComboBox, QSpinBox, QLineEdit, QLabel, QListWidget, QListWidgetItem,
    QTextBrowser, QMessageBox, QInputDialog, QProgressBar, QGroupBox, QCheckBox
)
from ai.provider_factory import AIProviderConfig, create_provider
from ai.providers import ProviderKind
from ai.question_provider import AIQuestionProvider
from ai.test_provider import TestQuestionProvider
from configuration.settings import Settings
from exporters.word_exporter import WordExporter
from models.assessment import GenerationRequest, Operation, ProfileName
from profiles.rules import default_quantity
from services.generation_service import GenerationService
from services.errors import MissingPlanError
from services.ollama_installer import OllamaInstallerService


class GeneratorWorker(QThread):
    progress = Signal(str, int)
    summary = Signal(str)
    done = Signal(str, str, str)
    failed = Signal(str)

    def __init__(self, request: GenerationRequest, ai_config: AIProviderConfig, use_local_test_provider: bool = False) -> None:
        super().__init__()
        self.request = request
        self.ai_config = ai_config
        self.use_local_test_provider = use_local_test_provider
        self.provider = None

    def run(self) -> None:
        try:
            if self.use_local_test_provider:
                provider = TestQuestionProvider()
            else:
                provider = AIQuestionProvider(create_provider(self.ai_config), self.ai_config.model)
            self.provider = provider
            service = GenerationService(provider)
            self.progress.emit("Validando arquivos", 5)
            self.progress.emit("Lendo PDFs", 15)
            self.progress.emit("Organizando conteúdos", 25)
            analysis = service.analyze(self.request)
            self.summary.emit(analysis.summary)
            self.progress.emit("Recuperando trechos", 40)
            self.progress.emit("Planejando questões", 50)
            self.progress.emit("Gerando questões", 65)
            result = service.generate(self.request)
            self.progress.emit("Validando", 78)
            self.progress.emit("Corrigindo", 86)
            exporter = WordExporter()
            self.progress.emit("Criando Word", 95)
            questions, answers, audit = exporter.export(result, self.request.output_dir, self.request.output_name)
            self.progress.emit("Concluído", 100)
            self.done.emit(str(questions), str(answers), str(audit))
        except MissingPlanError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Falha na geração: {exc}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("🎓 Assistente de Provas")
        self.resize(1080, 760)
        self.files: list[Path] = []
        self.settings = Settings()
        self.worker: GeneratorWorker | None = None
        self.ollama_installer = OllamaInstallerService()
        self.setAcceptDrops(True)
        self._build()

    def _build(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("🎓 Assistente de Provas")
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        layout.addWidget(title)
        row = QHBoxLayout()
        profile_box = QGroupBox("Perfil")
        profile_layout = QHBoxLayout(profile_box)
        self.profile = QComboBox(); self.profile.addItems([p.value for p in ProfileName])
        profile_layout.addWidget(self.profile)
        self.operation = QComboBox(); self.operation.addItems([o.value for o in Operation])
        self.profile.currentTextChanged.connect(self._set_default_quantity)
        self.operation.currentTextChanged.connect(self._set_default_quantity)
        row.addWidget(profile_box)
        row.addWidget(QLabel("Operação:")); row.addWidget(self.operation)
        layout.addLayout(row)

        ai_box = QGroupBox("Configuração da Inteligência Artificial")
        ai_layout = QHBoxLayout(ai_box)
        self.ai_provider = QComboBox(); self.ai_provider.addItems([kind.value for kind in ProviderKind])
        self.ai_host = QLineEdit("http://127.0.0.1:1234/v1")
        self.ai_model = QComboBox(); self.ai_model.setEditable(True); self.ai_model.addItem("local-model")
        self.ai_status = QLabel("Desconectado")
        self.only_materials = QCheckBox("Somente materiais enviados")
        self.only_materials.setChecked(True)
        check_btn = QPushButton("Verificar conexão"); check_btn.clicked.connect(self._check_ai_connection)
        models_btn = QPushButton("Atualizar modelos"); models_btn.clicked.connect(self._refresh_ai_models)
        self.install_ai_btn = QPushButton("Instalar IA Local"); self.install_ai_btn.clicked.connect(self._install_local_ai)
        self.install_model_btn = QPushButton("Instalar modelo recomendado"); self.install_model_btn.clicked.connect(self._install_recommended_model)
        self.ai_provider.currentTextChanged.connect(self._provider_changed)
        for label, widget in (("Provedor:", self.ai_provider), ("Endereço do servidor:", self.ai_host), ("Modelo:", self.ai_model)):
            ai_layout.addWidget(QLabel(label)); ai_layout.addWidget(widget)
        ai_layout.addWidget(check_btn); ai_layout.addWidget(models_btn); ai_layout.addWidget(self.only_materials); ai_layout.addWidget(self.install_ai_btn); ai_layout.addWidget(self.install_model_btn); ai_layout.addWidget(self.ai_status)
        layout.addWidget(ai_box)
        self._provider_changed(self.ai_provider.currentText())

        file_row = QHBoxLayout()
        add_btn = QPushButton("Selecionar Arquivos"); add_btn.clicked.connect(self._select_files)
        remove_btn = QPushButton("Remover Arquivos"); remove_btn.clicked.connect(self._remove_selected)
        file_row.addWidget(add_btn); file_row.addWidget(remove_btn)
        layout.addLayout(file_row)
        layout.addWidget(QLabel("Arquivos: Texto da Aula, Slides, Plano de Ensino (opcional), Material complementar"))
        self.file_list = QListWidget(); layout.addWidget(self.file_list)

        params = QHBoxLayout()
        self.aula = QLineEdit("Aula 1")
        self.quantity = QSpinBox(); self.quantity.setRange(1, 200)
        self.output_dir = QLineEdit(str(Path.home() / "Documents"))
        out_btn = QPushButton("Pasta de saída"); out_btn.clicked.connect(self._select_output)
        self.output_name = QLineEdit("questoes_uninter")
        for label, widget in (("Aula:", self.aula), ("Quantidade:", self.quantity), ("Saída:", self.output_dir), ("Nome:", self.output_name)):
            params.addWidget(QLabel(label)); params.addWidget(widget)
        params.addWidget(out_btn)
        layout.addLayout(params)

        actions = QHBoxLayout()
        cfg_btn = QPushButton("Configurar chave externa") ; cfg_btn.clicked.connect(self._configure_api)
        gen_btn = QPushButton("Gerar Provas"); gen_btn.clicked.connect(self._generate)
        cancel_btn = QPushButton("Cancelar"); cancel_btn.clicked.connect(self._cancel_generation)
        actions.addWidget(cfg_btn); actions.addWidget(gen_btn); actions.addWidget(cancel_btn)
        layout.addLayout(actions)
        self.progress_bar = QProgressBar(); self.progress_bar.setRange(0, 100); layout.addWidget(self.progress_bar)
        self.log = QTextBrowser(); self.log.setReadOnly(True); self.log.setOpenExternalLinks(True); layout.addWidget(self.log)
        self.setCentralWidget(root)
        self._set_default_quantity()
        QTimer.singleShot(250, self._first_run_ai_check)



    def _first_run_ai_check(self) -> None:
        self._check_ai_connection()

    def _install_local_ai(self) -> None:
        if QMessageBox.question(self, "Instalar IA Local", "Deseja instalar automaticamente o Ollama local gratuito agora?") != QMessageBox.StandardButton.Yes:
            return
        self.ai_status.setText("Instalando Ollama. Aguarde...")
        result = self.ollama_installer.install_ollama()
        if result.returncode == 0:
            self.ai_status.setText("Ollama instalado. Verificando novamente...")
            self._check_ai_connection()
        else:
            self.ai_status.setText("Falha ao instalar Ollama: " + (result.stderr or result.stdout or "erro desconhecido"))

    def _install_recommended_model(self) -> None:
        model = self.ai_model.currentText().strip() or self.ollama_installer.recommended_models()[0]
        if model not in self.ollama_installer.recommended_models() and QMessageBox.question(self, "Instalar modelo", f"Instalar o modelo selecionado '{model}'?") != QMessageBox.StandardButton.Yes:
            return
        self.ai_status.setText(f"Instalando modelo {model}. Este processo pode demorar...")
        result = self.ollama_installer.install_model(model)
        if result.returncode == 0:
            self.ai_model.setCurrentText(model)
            self.ai_status.setText(f"Modelo {model} instalado e definido como padrão.")
            self._refresh_ai_models()
        else:
            self.ai_status.setText("Falha ao instalar modelo: " + (result.stderr or result.stdout or "erro desconhecido"))

    def _provider_changed(self, provider_name: str) -> None:
        kind = ProviderKind(provider_name)
        is_ollama = kind == ProviderKind.OLLAMA
        self.install_ai_btn.setVisible(is_ollama)
        self.install_model_btn.setVisible(is_ollama)
        defaults = {
            ProviderKind.LM_STUDIO: ("http://127.0.0.1:1234/v1", "local-model", "Modo local: os documentos não são enviados para serviços externos."),
            ProviderKind.OLLAMA: ("http://localhost:11434", "llama3.1", "Modo local ativo via Ollama: sem chave de API e sem envio externo."),
            ProviderKind.OPENAI: ("https://api.openai.com/v1", "gpt-4.1-mini", "OpenAI externo opcional: exige chave e pode haver cobrança."),
            ProviderKind.GEMINI: ("https://generativelanguage.googleapis.com/v1beta", "gemini-1.5-flash", "Gemini externo opcional: exige chave e pode haver cobrança."),
            ProviderKind.CLAUDE: ("https://api.anthropic.com/v1", "claude-3-5-sonnet-latest", "Claude externo opcional: exige chave e pode haver cobrança."),
        }
        host, model, message = defaults[kind]
        self.ai_host.setText(host)
        self.ai_model.setCurrentText(model)
        self.ai_status.setText(message)

    def _ai_config(self) -> AIProviderConfig:
        kind = ProviderKind(self.ai_provider.currentText())
        api_key = self.settings.get_api_key() if kind in {ProviderKind.OPENAI, ProviderKind.GEMINI, ProviderKind.CLAUDE} else None
        return AIProviderConfig(kind=kind, base_url=self.ai_host.text().strip(), model=self.ai_model.currentText().strip(), api_key=api_key)

    def _check_ai_connection(self) -> None:
        status = create_provider(self._ai_config()).test_connection()
        self.ai_status.setText(status.status + ": " + status.message)
        if status.models:
            self._set_model_items(status.models)

    def _refresh_ai_models(self) -> None:
        status = create_provider(self._ai_config()).get_provider_status()
        self.ai_status.setText(status.status + ": " + status.message)
        self._set_model_items(status.models)

    def _set_model_items(self, models: list[str]) -> None:
        current = self.ai_model.currentText()
        self.ai_model.clear()
        if models:
            self.ai_model.addItems(models)
            if current in models:
                self.ai_model.setCurrentText(current)
        else:
            self.ai_model.addItem(current or "llama3.1")

    def _set_default_quantity(self) -> None:
        self.quantity.setValue(default_quantity(ProfileName(self.profile.currentText()), Operation(self.operation.currentText())))

    def _select_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Selecionar materiais", str(Path.home()), "Documentos (*.pdf *.docx *.txt);;PDF (*.pdf)")
        self._add_files([Path(p) for p in paths])

    def _add_files(self, paths: list[Path]) -> None:
        for path in paths:
            if path.exists() and path not in self.files:
                self.files.append(path)
        self._refresh_files()

    def _refresh_files(self) -> None:
        self.file_list.clear()
        for path in self.files:
            size = path.stat().st_size / 1024
            item = QListWidgetItem(f"{path.name} | {path.suffix.lower() or 'arquivo'} | {size:.1f} KB")
            item.setData(Qt.UserRole, str(path))
            self.file_list.addItem(item)

    def _remove_selected(self) -> None:
        selected = {Path(item.data(Qt.UserRole)) for item in self.file_list.selectedItems()}
        self.files = [path for path in self.files if path not in selected]
        self._refresh_files()

    def _select_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Pasta de saída", self.output_dir.text())
        if directory:
            self.output_dir.setText(directory)

    def _configure_api(self) -> None:
        key, ok = QInputDialog.getText(self, "Provedor externo", "Informe a chave somente se escolher provedor externo:")
        if ok and key.strip():
            self.settings.set_api_key(key.strip())
            QMessageBox.information(self, "Configuração", "Chave armazenada no cofre do sistema operacional.")

    def _generate(self) -> None:
        if not self.files:
            QMessageBox.warning(self, "Arquivos", "Selecione ao menos um PDF.")
            return
        request = GenerationRequest(
            profile=ProfileName(self.profile.currentText()), operation=Operation(self.operation.currentText()),
            aula=self.aula.text().strip() or "Aula", quantity=self.quantity.value(),
            output_dir=Path(self.output_dir.text()), output_name=self.output_name.text().strip() or "questoes_uninter",
            files=self.files,
            only_selected_materials=self.only_materials.isChecked(),
        )
        self.log.clear(); self.progress_bar.setValue(0); self.log.append("Iniciando...")
        self.worker = GeneratorWorker(request, self._ai_config())
        self.worker.progress.connect(self._progress)
        self.worker.summary.connect(lambda text: self.log.append("Resumo do conteúdo encontrado:\n" + text))
        self.worker.done.connect(self._done); self.worker.failed.connect(self._failed)
        self.worker.start()

    def _progress(self, message: str, value: int) -> None:
        self.progress_bar.setValue(value)
        self.log.append("• " + message)

    def _cancel_generation(self) -> None:
        if self.worker and self.worker.isRunning():
            if getattr(self.worker, "provider", None) and hasattr(self.worker.provider, "cancel_generation"):
                self.worker.provider.cancel_generation()
            self.worker.requestInterruption()
            self.log.append("Cancelamento solicitado.")

    def _done(self, questions: str, answers: str, audit: str) -> None:
        self.log.append("Concluído:")
        for label, path in (("Questões", questions), ("Gabarito", answers), ("Auditoria", audit)):
            self.log.append(f'<a href="file:///{path}">{label}: {path}</a>')
        QMessageBox.information(self, "Concluído", "Documentos Word criados com sucesso.")

    def _failed(self, message: str) -> None:
        self.log.append(message)
        QMessageBox.critical(self, "Erro", message)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        self._add_files([Path(url.toLocalFile()) for url in event.mimeData().urls()])
