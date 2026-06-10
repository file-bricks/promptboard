"""i18n-Layer für PromptBoard (Premium 6-Sprachen).

Deutsch ist Standardsprache. Weitere Sprachen via ``tr(key, 'en')`` oder via
globalen Switch ``set_language('en')``. Keine externen Dependencies.

Unterstützte Sprachen (Premium-Tier):
  de — Deutsch (Standard)
  en — English
  es — Español
  zh — 中文 (Chinesisch)
  ja — 日本語 (Japanisch)
  ru — Русский (Russisch)

Verwendung:
    from i18n import tr, set_language
    set_language("de")
    label.setText(tr("menu.file"))
"""
from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

LanguageCode = Literal["de", "en", "es", "zh", "ja", "ru"]
VALID_LANGUAGES: tuple[LanguageCode, ...] = ("de", "en", "es", "zh", "ja", "ru")
DEFAULT_LANGUAGE: LanguageCode = "de"

_TRANSLATIONS: dict[str, dict[LanguageCode, str]] = {
    # ----- Menüs ---------------------------------------------------------
    "menu.file": {
        "de": "&Datei", "en": "&File",
        "es": "&Archivo", "zh": "文件(&F)", "ja": "ファイル(&F)", "ru": "&Файл",
    },
    "menu.settings": {
        "de": "&Einstellungen", "en": "&Settings",
        "es": "&Configuración", "zh": "设置(&S)", "ja": "設定(&S)", "ru": "&Настройки",
    },
    "menu.file.new": {
        "de": "&Neuer Eintrag", "en": "&New entry",
        "es": "&Nueva entrada", "zh": "新建条目(&N)", "ja": "新規項目(&N)", "ru": "&Новая запись",
    },
    "menu.file.import_profiprompt": {
        "de": "Aus ProfiPrompt importieren",
        "en": "Import from ProfiPrompt",
        "es": "Importar desde ProfiPrompt", "zh": "从 ProfiPrompt 导入", "ja": "ProfiPrompt からインポート", "ru": "Импортировать из ProfiPrompt",
    },
    "menu.file.import_explorerpro": {
        "de": "Aus ExplorerPro importieren",
        "en": "Import from ExplorerPro",
        "es": "Importar desde ExplorerPro", "zh": "从 ExplorerPro 导入", "ja": "ExplorerPro からインポート", "ru": "Импортировать из ExplorerPro",
    },
    "menu.file.export_explorerpro": {
        "de": "Nach ExplorerPro exportieren",
        "en": "Export to ExplorerPro",
        "es": "Exportar a ExplorerPro", "zh": "导出到 ExplorerPro", "ja": "ExplorerPro へエクスポート", "ru": "Экспортировать в ExplorerPro",
    },
    "menu.file.quit": {
        "de": "Beenden", "en": "Quit",
        "es": "Salir", "zh": "退出", "ja": "終了", "ru": "Выйти",
    },
    "menu.settings.open": {
        "de": "Einstellungen…", "en": "Preferences…",
        "es": "Preferencias…", "zh": "首选项…", "ja": "環境設定…", "ru": "Настройки…",
    },

    # ----- Toolbar / Buttons --------------------------------------------
    "btn.new": {
        "de": "&Neu", "en": "&New",
        "es": "&Nuevo", "zh": "新建(&N)", "ja": "新規(&N)", "ru": "&Создать",
    },
    "btn.delete": {
        "de": "&Löschen", "en": "&Delete",
        "es": "&Eliminar", "zh": "删除(&D)", "ja": "削除(&D)", "ru": "&Удалить",
    },
    "btn.copy": {
        "de": "&Kopieren", "en": "&Copy",
        "es": "&Copiar", "zh": "复制(&C)", "ja": "コピー(&C)", "ru": "&Копировать",
    },
    "btn.copy_markdown": {
        "de": "Als Markdown kopieren", "en": "Copy as Markdown",
        "es": "Copiar como Markdown", "zh": "复制为 Markdown", "ja": "Markdown としてコピー", "ru": "Копировать как Markdown",
    },
    "btn.materialize": {
        "de": "&Materialisieren", "en": "&Materialize",
        "es": "&Materializar", "zh": "实体化(&M)", "ja": "マテリアライズ(&M)", "ru": "&Материализовать",
    },
    "btn.materialize_current": {
        "de": "Aktuellen Eintrag materialisieren",
        "en": "Materialize current entry",
        "es": "Materializar entrada actual", "zh": "实体化当前条目", "ja": "現在の項目をマテリアライズ", "ru": "Материализовать текущую запись",
    },
    "btn.materialize_selected": {
        "de": "Ausgewählte Einträge materialisieren",
        "en": "Materialize selected entries",
        "es": "Materializar entradas seleccionadas", "zh": "实体化选中条目", "ja": "選択した項目をマテリアライズ", "ru": "Материализовать выбранные записи",
    },
    "btn.change": {
        "de": "Ä&ndern…", "en": "&Change…",
        "es": "&Cambiar…", "zh": "更改(&C)", "ja": "変更(&C)", "ru": "&Изменить…",
    },
    "btn.ok": {
        "de": "&OK", "en": "&OK",
        "es": "&Aceptar", "zh": "确定(&O)", "ja": "&OK", "ru": "&ОК",
    },
    "btn.cancel": {
        "de": "&Abbrechen", "en": "&Cancel",
        "es": "&Cancelar", "zh": "取消(&C)", "ja": "キャンセル(&C)", "ru": "&Отмена",
    },

    # ----- Filter / Liste ------------------------------------------------
    "filter.all": {
        "de": "ALLE", "en": "ALL",
        "es": "TODO", "zh": "全部", "ja": "すべて", "ru": "ВСЕ",
    },
    "filter.search_placeholder": {
        "de": "Suche nach Name, Inhalt oder Kategorie…",
        "en": "Search by name, content, or category…",
        "es": "Buscar por nombre, contenido o categoría…", "zh": "按名称、内容或分类搜索…", "ja": "名前、内容、またはカテゴリで検索…", "ru": "Поиск по имени, содержимому или категории…",
    },
    "filter.type_name": {
        "de": "Typfilter", "en": "Type filter",
        "es": "Filtro de tipo", "zh": "类型筛选", "ja": "タイプフィルター", "ru": "Фильтр по типу",
    },
    "filter.type_description": {
        "de": "Bibliothek nach Eintragstyp filtern",
        "en": "Filter the library by entry type",
        "es": "Filtrar la biblioteca por tipo de entrada", "zh": "按条目类型过滤库", "ja": "ライブラリを項目タイプでフィルター", "ru": "Фильтровать библиотеку по типу записи",
    },
    "filter.sort_name": {
        "de": "Sortierung", "en": "Sort order",
        "es": "Ordenación", "zh": "排序方式", "ja": "並べ替え", "ru": "Порядок сортировки",
    },
    "filter.sort_description": {
        "de": "Sortierung der Bibliothek ändern",
        "en": "Change the library sort order",
        "es": "Cambiar el orden de clasificación de la biblioteca", "zh": "更改库排序方式", "ja": "ライブラリの並べ替え順を変更", "ru": "Изменить порядок сортировки библиотеки",
    },
    "filter.search_name": {
        "de": "Bibliothek durchsuchen", "en": "Search library",
        "es": "Buscar en la biblioteca", "zh": "搜索库", "ja": "ライブラリを検索", "ru": "Поиск по библиотеке",
    },
    "filter.search_description": {
        "de": "Bibliothek nach Name, Inhalt oder Kategorie durchsuchen",
        "en": "Search the library by name, content, or category",
        "es": "Buscar en la biblioteca por nombre, contenido o categoría", "zh": "按名称、内容或分类搜索库", "ja": "ライブラリを名前、内容、またはカテゴリで検索", "ru": "Поиск по библиотеке по имени, содержимому или категории",
    },

    # ----- Form-Labels ---------------------------------------------------
    "form.type": {
        "de": "Typ", "en": "Type",
        "es": "Tipo", "zh": "类型", "ja": "タイプ", "ru": "Тип",
    },
    "form.name": {
        "de": "Name", "en": "Name",
        "es": "Nombre", "zh": "名称", "ja": "名前", "ru": "Название",
    },
    "form.category": {
        "de": "Kategorie", "en": "Category",
        "es": "Categoría", "zh": "分类", "ja": "カテゴリ", "ru": "Категория",
    },
    "form.tags": {
        "de": "Tags", "en": "Tags",
        "es": "Etiquetas", "zh": "标签", "ja": "タグ", "ru": "Теги",
    },
    "form.source": {
        "de": "Quelle", "en": "Source",
        "es": "Fuente", "zh": "来源", "ja": "ソース", "ru": "Источник",
    },
    "form.source_placeholder": {
        "de": "z. B. lokal, ProfiPrompt, ExplorerPro",
        "en": "e.g. local, ProfiPrompt, ExplorerPro",
        "es": "p. ej. local, ProfiPrompt, ExplorerPro", "zh": "例如 local, ProfiPrompt, ExplorerPro", "ja": "例: local, ProfiPrompt, ExplorerPro", "ru": "например, локальный, ProfiPrompt, ExplorerPro",
    },
    "form.content_placeholder": {
        "de": "Inhalt des Eintrags… Platzhalter wie {{name}} werden beim Kopieren abgefragt.",
        "en": "Entry content… Placeholders like {{name}} are prompted when copying.",
        "es": "Contenido de la entrada… Los marcadores como {{name}} se solicitarán al copiar.", "zh": "条目内容… 复制时会提示输入 {{name}} 等占位符的值。", "ja": "項目の内容… コピー時に {{name}} のようなプレースホルダーの入力が求められます。", "ru": "Содержимое записи… При копировании будет предложено ввести значения для плейсхолдеров вроде {{name}}.",
    },

    # ----- Settings-Dialog ----------------------------------------------
    "settings.title": {
        "de": "PromptBoard – Einstellungen", "en": "PromptBoard — Settings",
        "es": "PromptBoard – Configuración", "zh": "PromptBoard – 设置", "ja": "PromptBoard – 設定", "ru": "PromptBoard – Настройки",
    },
    "settings.group.paths": {
        "de": "Pfade", "en": "Paths",
        "es": "Rutas", "zh": "路径", "ja": "パス", "ru": "Пути",
    },
    "settings.path.materialize": {
        "de": "Materialisierung", "en": "Materialization",
        "es": "Materialización", "zh": "实体化", "ja": "マテリアライズ", "ru": "Материализация",
    },
    "settings.path.profiprompt": {
        "de": "ProfiPrompt-Ordner", "en": "ProfiPrompt folder",
        "es": "Carpeta ProfiPrompt", "zh": "ProfiPrompt 文件夹", "ja": "ProfiPrompt フォルダ", "ru": "Папка ProfiPrompt",
    },
    "settings.path.explorerpro": {
        "de": "ExplorerPro-Ordner", "en": "ExplorerPro folder",
        "es": "Carpeta ExplorerPro", "zh": "ExplorerPro 文件夹", "ja": "ExplorerPro フォルダ", "ru": "Папка ExplorerPro",
    },
    "settings.group.io": {
        "de": "Import / Export", "en": "Import / Export",
        "es": "Importar / Exportar", "zh": "导入 / 导出", "ja": "インポート / エクスポート", "ru": "Импорт / Экспорт",
    },
    "settings.io.import_profiprompt": {
        "de": "Aus ProfiPrompt importieren",
        "en": "Import from ProfiPrompt",
        "es": "Importar desde ProfiPrompt", "zh": "从 ProfiPrompt 导入", "ja": "ProfiPrompt からインポート", "ru": "Импортировать из ProfiPrompt",
    },
    "settings.io.import_explorerpro": {
        "de": "Aus ExplorerPro importieren",
        "en": "Import from ExplorerPro",
        "es": "Importar desde ExplorerPro", "zh": "从 ExplorerPro 导入", "ja": "ExplorerPro からインポート", "ru": "Импортировать из ExplorerPro",
    },
    "settings.io.export_explorerpro": {
        "de": "Nach ExplorerPro exportieren",
        "en": "Export to ExplorerPro",
        "es": "Exportar a ExplorerPro", "zh": "导出到 ExplorerPro", "ja": "ExplorerPro へエクスポート", "ru": "Экспортировать в ExplorerPro",
    },
    "settings.group.view": {
        "de": "Ansicht", "en": "Appearance",
        "es": "Apariencia", "zh": "外观", "ja": "外観", "ru": "Внешний вид",
    },
    "settings.view.theme": {
        "de": "Farbschema", "en": "Color theme",
        "es": "Tema de color", "zh": "颜色主题", "ja": "カラーテーマ", "ru": "Цветовая тема",
    },
    "settings.view.language": {
        "de": "Sprache", "en": "Language",
        "es": "Idioma", "zh": "语言", "ja": "言語", "ru": "Язык",
    },
    "settings.view.confirm_overwrite": {
        "de": "Vor Überschreiben beim Materialisieren nachfragen",
        "en": "Confirm before overwriting on materialize",
        "es": "Confirmar antes de sobrescribir al materializar", "zh": "在实体化覆盖前确认", "ja": "マテリアライズ時の上書き前に確認する", "ru": "Подтверждать перед перезаписью при материализации",
    },
    "settings.group.info": {
        "de": "Info", "en": "Info",
        "es": "Información", "zh": "关于", "ja": "情報", "ru": "Информация",
    },
    "settings.info.data_dir": {
        "de": "Datenordner", "en": "Data folder",
        "es": "Carpeta de datos", "zh": "数据文件夹", "ja": "データフォルダ", "ru": "Папка данных",
    },
    "settings.info.log_file": {
        "de": "Logdatei", "en": "Log file",
        "es": "Archivo de log", "zh": "日志文件", "ja": "ログファイル", "ru": "Файл лога",
    },

    # ----- Theme-Namen ---------------------------------------------------
    "theme.system": {
        "de": "System", "en": "System",
        "es": "Sistema", "zh": "系统", "ja": "システム", "ru": "Системная",
    },
    "theme.light": {
        "de": "Hell", "en": "Light",
        "es": "Claro", "zh": "浅色", "ja": "ライト", "ru": "Светлая",
    },
    "theme.dark": {
        "de": "Dunkel", "en": "Dark",
        "es": "Oscuro", "zh": "深色", "ja": "ダーク", "ru": "Темная",
    },
    "theme.vibrant": {
        "de": "Vibrant (bunt)", "en": "Vibrant",
        "es": "Vibrante", "zh": "鲜艳", "ja": "バイブラント", "ru": "Яркая",
    },

    # ----- Sprach-Namen --------------------------------------------------
    "lang.de": {
        "de": "Deutsch", "en": "German",
        "es": "Alemán", "zh": "德语", "ja": "ドイツ語", "ru": "Немецкий",
    },
    "lang.en": {
        "de": "Englisch", "en": "English",
        "es": "Inglés", "zh": "英语", "ja": "英語", "ru": "Английский",
    },
    "lang.es": {
        "de": "Spanisch", "en": "Spanish",
        "es": "Español", "zh": "西班牙语", "ja": "スペイン語", "ru": "Испанский",
    },
    "lang.zh": {
        "de": "Chinesisch", "en": "Chinese",
        "es": "Chino", "zh": "中文", "ja": "中国語", "ru": "Китайский",
    },
    "lang.ja": {
        "de": "Japanisch", "en": "Japanese",
        "es": "Japonés", "zh": "日本語", "ja": "日本語", "ru": "Японский",
    },
    "lang.ru": {
        "de": "Russisch", "en": "Russian",
        "es": "Ruso", "zh": "俄语", "ja": "ロシア語", "ru": "Русский",
    },

    # ----- Statusmeldungen ----------------------------------------------
    "status.ready": {
        "de": "Bereit", "en": "Ready",
        "es": "Listo", "zh": "准备就绪", "ja": "準備完了", "ru": "Готово",
    },
    "status.editing": {
        "de": "Bearbeite: {name}", "en": "Editing: {name}",
        "es": "Editando: {name}", "zh": "正在编辑: {name}", "ja": "編集中の項目: {name}", "ru": "Редактирование: {name}",
    },
    "status.autosaved": {
        "de": "Automatisch gespeichert: {name}",
        "en": "Auto-saved: {name}",
        "es": "Guardado automáticamente: {name}", "zh": "已自动保存: {name}", "ja": "自動保存完了: {name}", "ru": "Автоматически сохранено: {name}",
    },
    "status.created": {
        "de": "Neuer Eintrag erstellt", "en": "New entry created",
        "es": "Nueva entrada creada", "zh": "已创建新条目", "ja": "新規項目が作成されました", "ru": "Создана новая запись",
    },
    "status.copied": {
        "de": "In Zwischenablage kopiert: {name}",
        "en": "Copied to clipboard: {name}",
        "es": "Copiado al portapapeles: {name}", "zh": "已复制到剪贴板: {name}", "ja": "クリップボードにコピーされました: {name}", "ru": "Скопировано в буфер обмена: {name}",
    },
    "status.copied_markdown": {
        "de": "Als Markdown kopiert: {name}",
        "en": "Copied as Markdown: {name}",
        "es": "Copiado como Markdown: {name}", "zh": "已复制为 Markdown: {name}", "ja": "Markdown としてコピーされました: {name}", "ru": "Скопировано как Markdown: {name}",
    },
    "status.copy_cancelled": {
        "de": "Kopieren abgebrochen",
        "en": "Copy cancelled",
        "es": "Copia cancelada", "zh": "复制已取消", "ja": "コピーがキャンセルされました", "ru": "Копирование отменено",
    },
    "status.copy_markdown_cancelled": {
        "de": "Markdown-Kopie abgebrochen",
        "en": "Markdown copy cancelled",
        "es": "Copia de Markdown cancelada", "zh": "Markdown 复制已取消", "ja": "Markdown コピーがキャンセルされました", "ru": "Копирование как Markdown отменено",
    },
    "status.materialized": {
        "de": "Materialisiert: {target}", "en": "Materialized: {target}",
        "es": "Materializado: {target}", "zh": "已实体化: {target}", "ja": "マテリアライズ完了: {target}", "ru": "Материализовано: {target}",
    },
    "status.materialized_batch": {
        "de": "{count} Einträge materialisiert: {target}",
        "en": "Materialized {count} entries: {target}",
        "es": "{count} entradas materializadas: {target}", "zh": "已实体化 {count} 个条目: {target}", "ja": "{count} 個の項目がマテリアライズされました: {target}", "ru": "Материализовано записей ({count}): {target}",
    },
    "status.materialize_cancelled": {
        "de": "Materialisierung abgebrochen",
        "en": "Materialization cancelled",
        "es": "Materialización cancelada", "zh": "实体化已取消", "ja": "マテリアライズがキャンセルされました", "ru": "Материализация отменена",
    },
    "status.delete_cancelled": {
        "de": "Löschen abgebrochen: {name}",
        "en": "Delete cancelled: {name}",
        "es": "Eliminación cancelada: {name}", "zh": "删除已取消: {name}", "ja": "削除がキャンセルされました: {name}", "ru": "Удаление отменено: {name}",
    },
    "status.deleted": {
        "de": "Gelöscht: {name}", "en": "Deleted: {name}",
        "es": "Eliminado: {name}", "zh": "已删除: {name}", "ja": "削除完了: {name}", "ru": "Удалено: {name}",
    },
    "status.minimized_to_tray": {
        "de": "Fenster in den Systemtray minimiert",
        "en": "Window minimized to system tray",
        "es": "Ventana minimizada al área de notificación", "zh": "窗口已最小化到系统托盘", "ja": "ウィンドウがシステムトレイに最小化されました", "ru": "Окно свернуто в системный трей",
    },
    "status.theme_updated": {
        "de": "Farbschema aktualisiert: {mode}",
        "en": "Theme updated: {mode}",
        "es": "Tema actualizado: {mode}", "zh": "主题已更新: {mode}", "ja": "テーマが更新されました: {mode}", "ru": "Tema оновлена: {mode}",
    },
    "status.language_updated": {
        "de": "Sprache geändert: {lang}",
        "en": "Language changed: {lang}",
        "es": "Idioma cambiado: {lang}", "zh": "语言已更改: {lang}", "ja": "言語が変更されました: {lang}", "ru": "Язык изменен: {lang}",
    },
    "status.materialize_path_set": {
        "de": "Neuer Materialisierungspfad: {path}",
        "en": "New materialize path: {path}",
        "es": "Nueva ruta de materialización: {path}", "zh": "新实体化路径: {path}", "ja": "新しいマテリアライズパス: {path}", "ru": "Новый путь материализации: {path}",
    },
    "status.hotkeys_enabled": {
        "de": "Globale Hotkeys aktiv: {show} / {copy}",
        "en": "Global hotkeys active: {show} / {copy}",
        "es": "Hotkeys globales activos: {show} / {copy}", "zh": "全局快捷键已激活: {show} / {copy}", "ja": "グローバルホットキーが有効: {show} / {copy}", "ru": "Глобальные горячие клавиши активны: {show} / {copy}",
    },
    "status.hotkeys_unavailable": {
        "de": "Globale Hotkeys nicht verfügbar; Systemtray bleibt aktiv",
        "en": "Global hotkeys unavailable; system tray remains active",
        "es": "Hotkeys globales no disponibles; el área de notificación permanece activa", "zh": "全局快捷键不可用；系统托盘保持活动状态", "ja": "グローバルホットキーは利用できません。システムトレイは有効なままです", "ru": "Глобальные горячие клавиши недоступны; системный трей остается активным",
    },
    "status.hotkeys_toggle_shown": {
        "de": "Fenster über Hotkey eingeblendet",
        "en": "Window shown via hotkey",
        "es": "Ventana mostrada mediante hotkey", "zh": "已通过快捷键显示窗口", "ja": "ホットキーによりウィンドウが表示されました", "ru": "Окно показано с помощью горячей клавиши",
    },
    "status.hotkeys_toggle_hidden": {
        "de": "Fenster über Hotkey ausgeblendet",
        "en": "Window hidden via hotkey",
        "es": "Ventana oculta mediante hotkey", "zh": "已通过快捷键隐藏窗口", "ja": "ホットキーによりウィンドウが非表示になりました", "ru": "Окно скрыто с помощью горячей клавиши",
    },
    "status.hotkeys_no_recent_item": {
        "de": "Kein zuletzt benutzter Eintrag für die Schnellkopie gefunden",
        "en": "No recently used entry found for quick copy",
        "es": "No se encontró ninguna entrada reciente para copia rápida", "zh": "未找到用于快速复制的最近条目", "ja": "クイックコピー用の最近使用した項目が見つかりません", "ru": "Не найдено недавно использовавшихся записей для быстрого копирования",
    },
    "status.hotkeys_quick_copy": {
        "de": "Schnellkopie per Hotkey: {name}",
        "en": "Quick copy via hotkey: {name}",
        "es": "Copia rápida mediante hotkey: {name}", "zh": "已通过快捷键快速复制: {name}", "ja": "ホットキーによるクイックコピー: {name}", "ru": "Быстрое копирование горячей клавишей: {name}",
    },
    "status.profiprompt_path_set": {
        "de": "Neuer ProfiPrompt-Pfad: {path}",
        "en": "New ProfiPrompt path: {path}",
        "es": "Nueva ruta de ProfiPrompt: {path}", "zh": "新 ProfiPrompt 路径: {path}", "ja": "新しい ProfiPrompt パス: {path}", "ru": "Новый путь ProfiPrompt: {path}",
    },
    "status.explorerpro_path_set": {
        "de": "Neuer ExplorerPro-Pfad: {path}",
        "en": "New ExplorerPro path: {path}",
        "es": "Nueva ruta de ExplorerPro: {path}", "zh": "新 ExplorerPro 路径: {path}", "ja": "新しい ExplorerPro パス: {path}", "ru": "Новый путь ExplorerPro: {path}",
    },
    "status.imported_profiprompt": {
        "de": "Importiert aus ProfiPrompt: {count} Einträge",
        "en": "Imported from ProfiPrompt: {count} entries",
        "es": "Importado desde ProfiPrompt: {count} entradas", "zh": "已从 ProfiPrompt 导入: {count} 个条目", "ja": "ProfiPrompt からインポートされました: {count} 件の項目", "ru": "Импортировано из ProfiPrompt: записей ({count})",
    },
    "status.imported_explorerpro": {
        "de": "Importiert aus ExplorerPro: {count} Einträge",
        "en": "Imported from ExplorerPro: {count} entries",
        "es": "Importado desde ExplorerPro: {count} entradas", "zh": "已从 ExplorerPro 导入: {count} 个条目", "ja": "ExplorerPro からインポートされました: {count} 件の項目", "ru": "Импортировано из ExplorerPro: записей ({count})",
    },
    "status.exported_explorerpro": {
        "de": "Nach ExplorerPro exportiert: {count} Einträge",
        "en": "Exported to ExplorerPro: {count} entries",
        "es": "Exportado a ExplorerPro: {count} entradas", "zh": "已导出到 ExplorerPro: {count} 个条目", "ja": "ExplorerPro へエクスポートされました: {count} 件の項目", "ru": "Экспортировано в ExplorerPro: записей ({count})",
    },

    # ----- Dialoge / Fehler ---------------------------------------------
    "dialog.delete.title": {
        "de": "Eintrag löschen", "en": "Delete entry",
        "es": "Eliminar entrada", "zh": "删除条目", "ja": "項目を削除", "ru": "Удалить запись",
    },
    "dialog.delete.body": {
        "de": "Möchtest du den Eintrag '{name}' wirklich löschen?",
        "en": "Really delete entry '{name}'?",
        "es": "¿Realmente desea eliminar la entrada '{name}'?", "zh": "确定要删除条目 '{name}' 吗？", "ja": "本当に項目 '{name}' を削除しますか？", "ru": "Вы действительно хотите удалить запись '{name}'?",
    },
    "dialog.overwrite.title": {
        "de": "Datei überschreiben?", "en": "Overwrite file?",
        "es": "¿Sobrescribir archivo?", "zh": "覆盖文件吗？", "ja": "ファイルを上書きしますか？", "ru": "Перезаписать файл?",
    },
    "dialog.overwrite.body": {
        "de": "'{name}' existiert bereits. Überschreiben?",
        "en": "'{name}' already exists. Overwrite?",
        "es": "'{name}' ya existe. ¿Sobrescribir?", "zh": "'{name}' 已存在。覆盖吗？", "ja": "'{name}' は既に存在します。上書きしますか？", "ru": "'{name}' уже существует. Перезаписать?",
    },
    "dialog.inline_variable.title": {
        "de": "Variable: {name}",
        "en": "Variable: {name}",
        "es": "Variable: {name}", "zh": "变量: {name}", "ja": "変数: {name}", "ru": "Переменная: {name}",
    },
    "dialog.inline_variable.body": {
        "de": "Wert für '{name}' eingeben:",
        "en": "Enter value for '{name}':",
        "es": "Introducir valor para '{name}':", "zh": "输入 '{name}' 的值:", "ja": "'{name}' の値を入力してください:", "ru": "Введите значение для '{name}':",
    },
    "dialog.import_failed.title": {
        "de": "Import fehlgeschlagen", "en": "Import failed",
        "es": "Error de importación", "zh": "导入失败", "ja": "インポート失敗", "ru": "Ошибка импорта",
    },
    "dialog.import_failed.profiprompt": {
        "de": "Kein ProfiPrompt-`prompts.json` mit mindestens einem Prompt gefunden.",
        "en": "No ProfiPrompt `prompts.json` with at least one prompt found.",
        "es": "No se encontró ningún `prompts.json` de ProfiPrompt con al menos un prompt.", "zh": "未找到至少包含一个提示词的 ProfiPrompt `prompts.json` 文件。", "ja": "少なくとも1つのプロンプトを含む ProfiPrompt の `prompts.json` が見つかりません。", "ru": "Не найден файл ProfiPrompt `prompts.json` с хотя бы одним промптом.",
    },
    "dialog.import_failed.explorerpro": {
        "de": "Kein ExplorerPro-`prompts.json` mit mindestens einem Prompt gefunden.",
        "en": "No ExplorerPro `prompts.json` with at least one prompt found.",
        "es": "No se encontró ningún `prompts.json` de ExplorerPro con al menos un prompt.", "zh": "未找到至少包含一个提示词的 ExplorerPro `prompts.json` 文件。", "ja": "少なくとも1つのプロンプトを含む ExplorerPro の `prompts.json` が見つかりません。", "ru": "Не найден файл ExplorerPro `prompts.json` с хотя бы одним промптом.",
    },
    "dialog.export_empty.title": {
        "de": "Export", "en": "Export",
        "es": "Exportar", "zh": "导出", "ja": "エクスポート", "ru": "Экспорт",
    },
    "dialog.export_empty.body": {
        "de": "Es gibt keine PROMPT-Einträge zum Export nach ExplorerPro.",
        "en": "No PROMPT entries available to export to ExplorerPro.",
        "es": "No hay entradas de PROMPT disponibles para exportar a ExplorerPro.", "zh": "无可用 PROMPT 条目导出到 ExplorerPro。", "ja": "ExplorerPro へエクスポートできる PROMPT 項目はありません。", "ru": "Нет записей PROMPT для экспорта в ExplorerPro.",
    },
    "dialog.choose_materialize_path": {
        "de": "Materialisierungspfad wählen",
        "en": "Choose materialize folder",
        "es": "Seleccionar carpeta de materialización", "zh": "选择实体化文件夹", "ja": "マテリアライズフォルダを選択", "ru": "Выбрать папку материализации",
    },
    "dialog.choose_profiprompt_path": {
        "de": "ProfiPrompt-Datenordner wählen",
        "en": "Choose ProfiPrompt data folder",
        "es": "Seleccionar carpeta de datos de ProfiPrompt", "zh": "选择 ProfiPrompt 数据文件夹", "ja": "ProfiPrompt データフォルダを選択", "ru": "Выбрать папку данных ProfiPrompt",
    },
    "dialog.choose_explorerpro_path": {
        "de": "ExplorerPro-Datenordner wählen",
        "en": "Choose ExplorerPro data folder",
        "es": "Seleccionar carpeta de datos de ExplorerPro", "zh": "选择 ExplorerPro 数据文件夹", "ja": "ExplorerPro データフォルダを選択", "ru": "Выбрать папку данных ExplorerPro",
    },
    "error.library_load": {
        "de": "Bibliothek konnte nicht geladen werden",
        "en": "Library could not be loaded",
        "es": "No se pudo cargar la biblioteca", "zh": "无法加载库", "ja": "ライブラリを読み込めませんでした", "ru": "Не удалось загрузить библиотеку",
    },
    "error.save_failed": {
        "de": "Speichern fehlgeschlagen", "en": "Save failed",
        "es": "Error al guardar", "zh": "保存失败", "ja": "保存失敗", "ru": "Ошибка сохранения",
    },
    "error.create_failed": {
        "de": "Eintrag konnte nicht angelegt werden",
        "en": "Entry could not be created",
        "es": "No se pudo crear la entrada", "zh": "无法创建条目", "ja": "項目を作成できませんでした", "ru": "Не удалось создать запись",
    },
    "error.delete_failed": {
        "de": "Löschen fehlgeschlagen", "en": "Delete failed",
        "es": "Error al eliminar", "zh": "删除失败", "ja": "削除失敗", "ru": "Ошибка удаления",
    },
    "error.materialize_failed": {
        "de": "Materialisierung fehlgeschlagen",
        "en": "Materialization failed",
        "es": "Error de materialización", "zh": "实体化失败", "ja": "マテリアライズ失敗", "ru": "Ошибка материализации",
    },
    "error.profiprompt_failed": {
        "de": "ProfiPrompt-Import fehlgeschlagen",
        "en": "ProfiPrompt import failed",
        "es": "Error al importar desde ProfiPrompt", "zh": "ProfiPrompt 导入失败", "ja": "ProfiPrompt インポート失敗", "ru": "Ошибка импорта из ProfiPrompt",
    },
    "error.explorerpro_import_failed": {
        "de": "ExplorerPro-Import fehlgeschlagen",
        "en": "ExplorerPro import failed",
        "es": "Error al importar desde ExplorerPro", "zh": "ExplorerPro 导入失败", "ja": "ExplorerPro インポート失敗", "ru": "Ошибка импорта из ExplorerPro",
    },
    "error.explorerpro_export_failed": {
        "de": "ExplorerPro-Export fehlgeschlagen",
        "en": "ExplorerPro export failed",
        "es": "Error al exportar a ExplorerPro", "zh": "ExplorerPro 导出失败", "ja": "ExplorerPro エクスポート失敗", "ru": "Ошибка экспорта в ExplorerPro",
    },

    # ----- Tray ----------------------------------------------------------
    "tray.open": {
        "de": "Öffnen", "en": "Open",
        "es": "Abrir", "zh": "打开", "ja": "開く", "ru": "Открыть",
    },
    "tray.hide": {
        "de": "Verstecken", "en": "Hide",
        "es": "Ocultar", "zh": "非表示", "ja": "非表示にする", "ru": "Скрыть",
    },
    "tray.quit": {
        "de": "Beenden", "en": "Quit",
        "es": "Salir", "zh": "退出", "ja": "終了", "ru": "Выйти",
    },

    # ----- Tooltips & Accessible Names ------------------------------------
    "btn.new.tooltip": {
        "de": "Erstellt einen neuen Bibliothekseintrag", "en": "Create a new library entry",
        "es": "Crear una nueva entrada en la biblioteca", "zh": "创建新的库条目", "ja": "新しいライブラリ項目を作成します", "ru": "Создать новую запись в библиотеке",
    },
    "btn.delete.tooltip": {
        "de": "Löscht den aktuell ausgewählten Eintrag", "en": "Delete the currently selected entry",
        "es": "Eliminar la entrada actualmente seleccionada", "zh": "删除当前选中的条目", "ja": "現在選択されている項目を削除します", "ru": "Удалить текущую выбранную запись",
    },
    "btn.copy.tooltip": {
        "de": "Kopiert den Inhalt in die Zwischenablage", "en": "Copy the content to the clipboard",
        "es": "Copiar el contenido al portapapeles", "zh": "将内容复制到剪贴板", "ja": "内容をクリップボードにコピーします", "ru": "Копировать содержимое в буфер обмена",
    },
    "btn.materialize.tooltip": {
        "de": "Schreibt den Eintrag als Markdown-Datei", "en": "Write the entry as a Markdown file",
        "es": "Escribir la entrada como un archivo Markdown", "zh": "将条目写入为 Markdown 文件", "ja": "項目を Markdown ファイルとして書き出します", "ru": "Записать запись как файл Markdown",
    },
    "form.type.tooltip": {
        "de": "Wähle den Typ des Eintrags (z. B. PROMPT, SKILL, AGENT)", "en": "Select the type of the entry (e.g., PROMPT, SKILL, AGENT)",
        "es": "Seleccione el tipo de entrada (p. ej., PROMPT, SKILL, AGENT)", "zh": "选择条目类型 (如 PROMPT, SKILL, AGENT)", "ja": "項目のタイプを選択します (例: PROMPT, SKILL, AGENT)", "ru": "Выберите тип записи (например, PROMPT, SKILL, AGENT)",
    },
    "form.name.tooltip": {
        "de": "Gib den Namen des Eintrags ein", "en": "Enter the name of the entry",
        "es": "Introduzca el nombre de la entrada", "zh": "输入条目名称", "ja": "項目の名前を入力します", "ru": "Введите имя записи",
    },
    "form.category.tooltip": {
        "de": "Gib eine Kategorie zur Organisation des Eintrags ein", "en": "Enter a category to organize the entry",
        "es": "Introduzca una categoría para organizar la entrada", "zh": "输入分类以组织条目", "ja": "項目を整理するためのカテゴリを入力します", "ru": "Введите категорию для организации записи",
    },
    "form.tags.tooltip": {
        "de": "Gib Tags ein, getrennt durch Kommata", "en": "Enter tags, separated by commas",
        "es": "Introduzca etiquetas, separadas por comas", "zh": "输入标签，用逗号分隔", "ja": "カンマで区切られたタグを入力します", "ru": "Введите теги через запятую",
    },
    "form.source.tooltip": {
        "de": "Gib die Herkunft des Eintrags an (z. B. lokal, ProfiPrompt)", "en": "Specify the origin of the entry (e.g., local, ProfiPrompt)",
        "es": "Especifique el origen de la entrada (p. ej., local, ProfiPrompt)", "zh": "指定条目的来源 (如 local, ProfiPrompt)", "ja": "項目の取得元を指定します (例: local, ProfiPrompt)", "ru": "Укажите источник записи (например, local, PromptBoard)",
    },
    "form.content": {
        "de": "Inhalt", "en": "Content",
        "es": "Contenido", "zh": "内容", "ja": "内容", "ru": "Содержимое",
    },
    "form.content.tooltip": {
        "de": "Gib den Textinhalt des Eintrags ein", "en": "Enter the text content of the entry",
        "es": "Introduzca el contenido de texto de la entrada", "zh": "输入条目的文本内容", "ja": "項目のテキスト内容を入力します", "ru": "Введите текстовое содержимое записи",
    },
    "settings.path.materialize.tooltip": {
        "de": "Pfad, in den Markdown-Dateien geschrieben werden", "en": "Path where Markdown files are written",
        "es": "Ruta donde se escriben los archivos Markdown", "zh": "写入 Markdown 文件的路径", "ja": "Markdown ファイルが書き出されるパス", "ru": "Путь, по которому записываются файлы Markdown",
    },
    "settings.btn.change.materialize.tooltip": {
        "de": "Materialisierungspfad ändern", "en": "Change materialize path",
        "es": "Cambiar ruta de materialización", "zh": "更改实体化路径", "ja": "マテリアライズパスを変更します", "ru": "Изменить путь материализации",
    },
    "settings.path.profiprompt.tooltip": {
        "de": "Pfad zum ProfiPrompt-Datenordner", "en": "Path to the ProfiPrompt data folder",
        "es": "Ruta a la carpeta de datos de ProfiPrompt", "zh": "ProfiPrompt 数据文件夹路径", "ja": "ProfiPrompt データフォルダへのパス", "ru": "Путь к папке данных ProfiPrompt",
    },
    "settings.btn.change.profiprompt.tooltip": {
        "de": "ProfiPrompt-Pfad ändern", "en": "Change ProfiPrompt path",
        "es": "Cambiar ruta de ProfiPrompt", "zh": "更改 ProfiPrompt 路径", "ja": "ProfiPrompt パスを変更します", "ru": "Изменить путь ProfiPrompt",
    },
    "settings.path.explorerpro.tooltip": {
        "de": "Pfad zum ExplorerPro-Datenordner", "en": "Path to the ExplorerPro data folder",
        "es": "Ruta a la carpeta de datos de ExplorerPro", "zh": "ExplorerPro 数据文件夹路径", "ja": "ExplorerPro データフォルダへのパス", "ru": "Путь к папке данных ExplorerPro",
    },
    "settings.btn.change.explorerpro.tooltip": {
        "de": "ExplorerPro-Pfad ändern", "en": "Change ExplorerPro path",
        "es": "Cambiar ruta de ExplorerPro", "zh": "更改 ExplorerPro 路径", "ja": "ExplorerPro パスを変更します", "ru": "Изменить путь ExplorerPro",
    },
    "settings.io.import_profiprompt.tooltip": {
        "de": "Einträge aus ProfiPrompt importieren", "en": "Import entries from ProfiPrompt",
        "es": "Importar entradas desde ProfiPrompt", "zh": "从 ProfiPrompt 导入条目", "ja": "ProfiPrompt から項目をインポートします", "ru": "Импортировать записи из ProfiPrompt",
    },
    "settings.io.import_explorerpro.tooltip": {
        "de": "Einträge aus ExplorerPro importieren", "en": "Import entries from ExplorerPro",
        "es": "Importar entradas desde ExplorerPro", "zh": "从 ExplorerPro 导入条目", "ja": "ExplorerPro から項目をインポートします", "ru": "Импортировать записи из ExplorerPro",
    },
    "settings.io.export_explorerpro.tooltip": {
        "de": "PROMPT-Einträge nach ExplorerPro exportieren", "en": "Export PROMPT entries to ExplorerPro",
        "es": "Exportar entradas de PROMPT a ExplorerPro", "zh": "将 PROMPT 条目导出到 ExplorerPro", "ja": "PROMPT 項目を ExplorerPro へエクスポートします", "ru": "Экспортировать записи PROMPT в ExplorerPro",
    },
    "settings.view.theme.tooltip": {
        "de": "Wähle das Farbschema", "en": "Select the color theme",
        "es": "Seleccionar el tema de color", "zh": "选择颜色主题", "ja": "カラーテーマを選択します", "ru": "Выбрать цветовую тему",
    },
    "settings.view.language.tooltip": {
        "de": "Wähle die Sprache", "en": "Select the language",
        "es": "Seleccionar el idioma", "zh": "选择语言", "ja": "言語を選択します", "ru": "Выбрать язык",
    },
    "settings.view.confirm_overwrite.tooltip": {
        "de": "Nachfragen, bevor eine Datei überschrieben wird", "en": "Ask before overwriting a file",
        "es": "Preguntar antes de sobrescribir un archivo", "zh": "覆盖文件前进行确认", "ja": "ファイルを上書きする前に確認します", "ru": "Спрашивать перед перезаписью файла",
    },
}

_current_language: LanguageCode = DEFAULT_LANGUAGE


def set_language(code: str) -> None:
    """Globaler Sprach-Switch."""
    global _current_language
    if code not in VALID_LANGUAGES:
        logger.warning("Ungültiger Sprach-Code '%s', verwende Default '%s'.", code, DEFAULT_LANGUAGE)
        _current_language = DEFAULT_LANGUAGE
        return
    _current_language = code  # type: ignore[assignment]


def get_language() -> LanguageCode:
    return _current_language


def tr(key: str, lang: str | None = None, **kwargs) -> str:
    """Translate a key. Falls back to DEFAULT_LANGUAGE or the key itself.

    ``**kwargs`` are forwarded to ``str.format`` for placeholders.
    """
    code: LanguageCode = (lang if lang in VALID_LANGUAGES else _current_language)  # type: ignore[assignment]
    entry = _TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(code) or entry.get(DEFAULT_LANGUAGE) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
