# Assistente de Provas

Aplicação desktop em Python 3.12 para gerar e revisar questões avaliativas a partir de PDFs selecionados pelo usuário, usando PySide6, PyMuPDF, python-docx e provedores locais de IA como Ollama/LM Studio.

## Execução em desenvolvimento

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
assistente-de-provas
```

No Linux/macOS, adapte a ativação do ambiente virtual.

## Uso

1. Abra o programa `Assistente de Provas`.
2. Use o provedor padrão **LM Studio Local** sem chave de API, ou escolha Ollama, OpenAI, Gemini ou Claude nas configurações.
3. Escolha o perfil **Grade Antiga** ou **Marco Regulatório**.
4. Selecione PDFs do texto da aula, slides, Plano de Ensino quando houver, complementares e banco existente.
5. Defina operação, aula, quantidade, pasta de saída e nome do documento.
6. Clique em **Gerar Provas** para criar `Questões.docx`, `Gabarito.docx` e `Relatório_Auditoria.docx`.

## Regras implementadas

- Grade Antiga: 5 alternativas, introdução mínima de 250 caracteres, gabarito, justificativas, referência, dificuldade e Taxonomia de Bloom; Plano de Ensino não bloqueia a geração.
- Marco Regulatório: 4 alternativas e bloqueio quando não houver Plano de Ensino para extrair competências e habilidades obrigatórias.
- Leitura integral dos PDFs por página, preservando arquivo, tipo e número da página.
- Mapa automático de temas e relatório de auditoria em Word.

## Testes

```bash
pip install -e .[dev]
pytest
```

## Build Windows

Execute no Windows com Python 3.12:

```powershell
scripts\build_windows.ps1
```

Depois compile `installer\assistente_de_provas.iss` no Inno Setup para gerar o instalador.

## Limitações conhecidas

- O executável e o instalador Windows precisam ser gerados em ambiente Windows com PyInstaller e Inno Setup instalados.
- Documentos `.docx` enviados como material complementar ainda não são lidos; o MVP lê PDFs para geração.
- LM Studio ou Ollama precisam estar instalados e com ao menos um modelo local disponível para geração local completa; provedores externos exigem chave própria.
