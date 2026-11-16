# Store Listing — PromptBoard

Stand: 2026-11-14 (Tier-2 6-Sprachen-Ausbau für `v1.1.3` / `1.1.3.0`)

## Einreichungsstatus

Die Store-Metadaten (`Geiger.PromptBoard`, `CN=52596601-BAB4-4F3F-B182-E8F3F273B202`,
Version `1.1.3.0`) und 6-Sprachen-Listings sind harmonisiert und über
`scripts/check_store_readiness.py` lokal validiert. Der abschließende lokale
MSIX-Build mit `makeappx.exe` und der erhöhte WACK-Lauf bleiben offene
Admin-/SDK-Ausführungsschritte vor dem Partner-Center-Upload.

---

## Deutsch

- **Name:** PromptBoard
- **Kurzbeschreibung:** Lokales Tray-Tool für Prompts, Skills, Workflows, Rollen und Agenten.
- **Kategorie:** Productivity
- **Altersfreigabe:** 3+

### Beschreibung

PromptBoard ist ein leichtgewichtiges, offline-first Desktop-Werkzeug für wiederverwendbare LLM-Bausteine. Die App verwaltet Prompts, Skills, Workflows, Rollen und Agenten lokal auf dem eigenen Gerät — schnell erreichbar über das System-Tray, globale Hotkeys und ein klares Zweispalt-Fenster.

**Funktionen:**

- Lokale Verwaltung von Prompts, Skills, Workflows, Rollen und Agenten (`~/.promptboard/library.json`)
- Schneller Tray-Zugriff nach Kategorie und Kopieren per Klick oder Doppelklick
- Globale Hotkeys zum Ein-/Ausblenden sowie zum Kopieren des zuletzt genutzten Eintrags
- Inline-Variablen (`{{name}}`) werden beim Kopieren komfortabel abgefragt
- Saubere Markdown-Materialisierung als `.md` oder `.txt` (inkl. Metadaten-Block)
- 6-Sprachen-Oberfläche live umschaltbar (`DE`, `EN`, `ES`, `ZH`, `JA`, `RU`) mit hellem/dunklem Design
- Barrierefreie Tastaturbedienung und Adapter für ProfiPrompt und ExplorerPro
- 100 % offline ohne Cloud-Zwang, Konten oder Telemetrie

### Screenshots

| Nr. | Datei | Ansicht |
|---|---|---|
| 01 | `README/screenshots/store/tray.png` | Tray-Menü mit Kategorie-Navigation |
| 02 | `README/screenshots/store/library.png` | Durchsuchbare Bibliothek mit Typfilter |
| 03 | `README/screenshots/store/editor.png` | Eintrags-Editor mit Live-Materialisierung |
| 04 | `README/screenshots/store/settings.png` | Einstellungen für Sprache, Pfade und Design |

### Keywords

prompts, prompt-manager, skills, workflows, markdown, zwischenablage, offline-tool

---

## English

- **Name:** PromptBoard
- **Short Description:** Local tray tool for prompts, skills, workflows, roles, and agents.
- **Category:** Productivity
- **Age Rating:** 3+

### Description

PromptBoard is a lightweight, offline-first desktop utility for reusable LLM building blocks. It manages prompts, skills, workflows, roles, and agents locally on your device — accessible in seconds from the system tray, global hotkeys, and a focused two-pane workspace.

**Features:**

- Local library for prompts, skills, workflows, roles, and agents (`~/.promptboard/library.json`)
- Quick tray menu organized by category with one-click clipboard copy
- Global hotkeys to toggle visibility and copy the last used entry
- Prompt placeholders (`{{name}}`) prompted automatically on copy
- Clean Markdown materialization as `.md` or `.txt` files
- 6-language UI (`DE`, `EN`, `ES`, `ZH`, `JA`, `RU`) with light, dark, and system themes
- Accessible keyboard navigation and adapters for ProfiPrompt and ExplorerPro
- 100% offline with zero cloud accounts or telemetry

### Screenshots

| No. | File | View |
|---|---|---|
| 01 | `README/screenshots/store/tray.png` | Tray menu with category navigation |
| 02 | `README/screenshots/store/library.png` | Searchable library with type filter |
| 03 | `README/screenshots/store/editor.png` | Entry editor with Markdown export |
| 04 | `README/screenshots/store/settings.png` | Language, paths, and theme settings |

### Keywords

prompts, prompt manager, skills, workflows, markdown, clipboard, offline tray

---

## Español (es-ES)

- **Nombre:** PromptBoard
- **Descripción corta:** Herramienta local en bandeja para prompts, skills, flujos, roles y agentes.
- **Categoría:** Productivity
- **Clasificación de edad:** 3+

### Descripción

PromptBoard es una utilidad de escritorio ligera y offline-first para bloques reutilizables de LLM. Administra prompts, habilidades, flujos de trabajo, roles y agentes de forma local, con acceso rápido desde la bandeja del sistema, atajos globales y exportación limpia a Markdown.

**Características:**

- Biblioteca local de prompts, habilidades, flujos, roles y agentes (`~/.promptboard/library.json`)
- Acceso rápido desde la bandeja por categoría y copia con un clic
- Atajos globales para mostrar la ventana y copiar el último elemento
- Sustitución interactiva de variables (`{{name}}`) al copiar
- Materialización limpia en archivos `.md` o `.txt`
- Interfaz en 6 idiomas (`DE`, `EN`, `ES`, `ZH`, `JA`, `RU`) con tema claro y oscuro
- 100 % sin conexión, sin cuentas en la nube ni telemetría

### Capturas de pantalla

| N.º | Archivo | Vista |
|---|---|---|
| 01 | `README/screenshots/store/tray.png` | Menú de bandeja por categoría |
| 02 | `README/screenshots/store/library.png` | Biblioteca con filtro de tipos |
| 03 | `README/screenshots/store/editor.png` | Editor con exportación a Markdown |
| 04 | `README/screenshots/store/settings.png` | Ajustes de idioma, rutas y tema |

### Palabras clave

prompts, gestor prompts, habilidades, flujos, markdown, portapapeles, sin conexion

---

## 简体中文 (zh-CN)

- **名称:** PromptBoard
- **简短描述:** 本地托盘工具，用于管理提示词、技能、工作流、角色与智能体。
- **类别:** Productivity
- **年龄分级:** 3+

### 说明

PromptBoard 是一款轻量、离线优先的桌面工具，用于管理可复用的 LLM 构建模块。它将提示词、技能、工作流、角色与智能体保存在本地，支持系统托盘快速访问、全局快捷键和干净的 Markdown 文件导出。

**核心功能:**

- 本地管理提示词、技能、工作流、角色与智能体（`~/.promptboard/library.json`）
- 按分类组织的系统托盘菜单，一键复制到剪贴板
- 全局快捷键切换窗口显示并快速复制最近使用的条目
- 复制时自动提示填写 `{{name}}` 等内联变量
- 支持导出为 `.md` 或 `.txt` 文件
- 6 种语言界面实时切换（`DE`、`EN`、`ES`、`ZH`、`JA`、`RU`），支持明暗主题
- 100% 纯离线运行，无需云账户或遥测

### 屏幕截图

| 序号 | 文件 | 视图 |
|---|---|---|
| 01 | `README/screenshots/store/tray.png` | 按分类导航的托盘菜单 |
| 02 | `README/screenshots/store/library.png` | 支持类型筛选的提示词库 |
| 03 | `README/screenshots/store/editor.png` | 支持 Markdown 导出的编辑器 |
| 04 | `README/screenshots/store/settings.png` | 语言、路径与外观设置 |

### 关键词

提示词, 提示词管理, 技能, 工作流, markdown, 剪贴板, 本地离线

---

## 日本語 (ja-JP)

- **名前:** PromptBoard
- **短い説明:** プロンプト・スキル・ワークフロー・ロール・エージェント向けのローカル常駐ツール。
- **カテゴリ:** Productivity
- **年齢区分:** 3+

### 説明

PromptBoard は、再利用可能な LLM 構成要素を管理する軽量でオフラインファーストなデスクトップツールです。プロンプト、スキル、ワークフロー、ロール、エージェントをローカルに保存し、タスクトレイからの素早いアクセス、グローバルホットキー、Markdown 出力を提供します。

**主な機能:**

- プロンプト・スキル・ワークフロー・ロール・エージェントのローカル管理（`~/.promptboard/library.json`）
- カテゴリ別トレイメニューからのワンクリックコピー
- ウィンドウ切り替えと直近項目のコピーに対応するグローバルホットキー
- コピー時のインライン変数（`{{name}}`）入力プロンプト
- `.md` / `.txt` 形式でのクリーンなマテリアライズ出力
- 6 言語 UI リアルタイム切り替え（`DE`・`EN`・`ES`・`ZH`・`JA`・`RU`）とライト/ダークテーマ
- クラウドアカウントやテレメトリ不要の完全オフライン動作

### スクリーンショット

| 番号 | ファイル | 画面 |
|---|---|---|
| 01 | `README/screenshots/store/tray.png` | カテゴリ別トレイメニュー |
| 02 | `README/screenshots/store/library.png` | タイプ別フィルター対応ライブラリ |
| 03 | `README/screenshots/store/editor.png` | Markdown 出力対応エディタ |
| 04 | `README/screenshots/store/settings.png` | 言語・パス・テーマ設定 |

### キーワード

プロンプト, プロンプト管理, スキル, ワークフロー, markdown, クリップボード, オフライン

---

## Русский (ru-RU)

- **Название:** PromptBoard
- **Краткое описание:** Локальная утилита в трее для промптов, навыков, процессов, ролей и агентов.
- **Категория:** Productivity
- **Возрастной рейтинг:** 3+

### Описание

PromptBoard — лёгкая настольная утилита с приоритетом офлайн-работы для многоразовых блоков LLM. Она хранит промпты, навыки, рабочие процессы, роли и агентов локально, обеспечивая быстрый доступ из системного трея, глобальные горячие клавиши и чистый экспорт в Markdown.

**Возможности:**

- Локальная библиотека промптов, навыков, процессов, ролей и агентов (`~/.promptboard/library.json`)
- Быстрый доступ по категориям из системного трея и копирование в один клик
- Глобальные горячие клавиши для окна и последнего использованного элемента
- Запрос встроенных переменных (`{{name}}`) при копировании
- Материализация в чистые файлы `.md` или `.txt`
- Интерфейс на 6 языках (`DE`, `EN`, `ES`, `ZH`, `JA`, `RU`) со светлой и тёмной темой
- Полностью офлайн: без облачных аккаунтов и телеметрии

### Скриншоты

| № | Файл | Экран |
|---|---|---|
| 01 | `README/screenshots/store/tray.png` | Меню трея с категориями |
| 02 | `README/screenshots/store/library.png` | Библиотека с фильтром типов |
| 03 | `README/screenshots/store/editor.png` | Редактор с экспортом в Markdown |
| 04 | `README/screenshots/store/settings.png` | Настройки языка, путей и темы |

### Ключевые слова

промпты, менеджджер промптов, навыки, процессы, markdown, буфер обмена, офлайн
