from __future__ import annotations

import sys
from functools import partial
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QStatusBar, QStyle, QToolBar, QTableWidget, QTableWidgetItem, QInputDialog, QListWidget, QVBoxLayout, QDialog, QDialogButtonBox, QLabel, QComboBox, QPushButton

from src.core.constants import ABOUT_TEXT, APP_TITLE, HELP_TEXT, TEXT_MENU_HINTS, TEXT_MENU_ITEMS, TEST_EXAMPLES
from src.core.file_service import read_text_file, write_text_file
from src.core.analyzer import scan_rust, Token, TokenType
from src.core.syntax_analyzer import parse_syntax, SyntaxError
from src.core.regex_search import RegexSearcher, MatchResult
from src.ui.editor_widgets import CodeEditor, build_editor_splitter


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.language = "ru"
        self.setAcceptDrops(True)

        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)

        self._setup_central_area()
        self._setup_status_bar()
        self._setup_actions()
        self._setup_menu()
        self._setup_toolbar()
        self.new_file()

    def _setup_central_area(self) -> None:
        splitter, editor_tabs, output_tabs, output_log, output_errors = build_editor_splitter()
        self.editor_tabs = editor_tabs
        self.output_tabs = output_tabs
        self.output_log = output_log
        self.output_errors = output_errors
        self.setCentralWidget(splitter)

        # Таблица лексем
        self.output_tokens = QTableWidget(0, 4)
        self.output_tokens.setHorizontalHeaderLabels([
            "Условный код",
            "Тип лексемы",
            "Лексема",
            "Местоположение"
        ])
        self.output_tokens.setAlternatingRowColors(True)
        self.output_tokens.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.output_tokens.cellDoubleClicked.connect(self._jump_to_token)
        self.output_tabs.addTab(self.output_tokens, "Лексемы")

        # Таблица результатов поиска по регулярным выражениям
        self.output_regex = QTableWidget(0, 4)
        self.output_regex.setHorizontalHeaderLabels([
            "Найденная подстрока",
            "Начальная позиция (строка:символ)",
            "Длина",
            "Тип поиска"
        ])
        self.output_regex.setAlternatingRowColors(True)
        self.output_regex.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.output_regex.cellDoubleClicked.connect(self._jump_to_regex_match)
        self.output_tabs.addTab(self.output_regex, "Поиск по РВ")

        self.editor_tabs.currentChanged.connect(lambda _: self._update_title())
        self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)
        self.output_errors.cellDoubleClicked.connect(self._jump_to_error)

    def _setup_status_bar(self) -> None:
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Готово")

    def _setup_actions(self) -> None:
        self.action_new = QAction("Создать", self)
        self.action_new.setIcon(self._icon("new.svg", QStyle.StandardPixmap.SP_FileIcon))
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self.new_file)

        self.action_open = QAction("Открыть", self)
        self.action_open.setIcon(self._icon("open.svg", QStyle.StandardPixmap.SP_DialogOpenButton))
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self.open_file)

        self.action_save = QAction("Сохранить", self)
        self.action_save.setIcon(self._icon("save.svg", QStyle.StandardPixmap.SP_DialogSaveButton))
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.triggered.connect(self.save_file)

        self.action_save_as = QAction("Сохранить как", self)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.triggered.connect(self.save_file_as)

        self.action_exit = QAction("Выход", self)
        self.action_exit.triggered.connect(self.close)

        self.action_undo = QAction("Отменить", self)
        self.action_undo.setIcon(self._icon("undo.svg", QStyle.StandardPixmap.SP_ArrowBack))
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.triggered.connect(lambda: self._current_editor().undo() if self._current_editor() else None)

        self.action_redo = QAction("Повторить", self)
        self.action_redo.setIcon(self._icon("redo.svg", QStyle.StandardPixmap.SP_ArrowForward))
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.triggered.connect(lambda: self._current_editor().redo() if self._current_editor() else None)

        self.action_cut = QAction("Вырезать", self)
        self.action_cut.setIcon(self._icon("cut.svg", QStyle.StandardPixmap.SP_TrashIcon))
        self.action_cut.setShortcut(QKeySequence.StandardKey.Cut)
        self.action_cut.triggered.connect(lambda: self._current_editor().cut() if self._current_editor() else None)

        self.action_copy = QAction("Копировать", self)
        self.action_copy.setIcon(self._icon("copy.svg", QStyle.StandardPixmap.SP_FileLinkIcon))
        self.action_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self.action_copy.triggered.connect(lambda: self._current_editor().copy() if self._current_editor() else None)

        self.action_paste = QAction("Вставить", self)
        self.action_paste.setIcon(self._icon("paste.svg", QStyle.StandardPixmap.SP_DialogApplyButton))
        self.action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.action_paste.triggered.connect(lambda: self._current_editor().paste() if self._current_editor() else None)

        self.action_delete = QAction("Удалить", self)
        self.action_delete.triggered.connect(self.delete_selected_text)

        self.action_select_all = QAction("Выделить все", self)
        self.action_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.action_select_all.triggered.connect(lambda: self._current_editor().selectAll() if self._current_editor() else None)

        self.action_start = QAction("Пуск", self)
        self.action_start.setShortcut(QKeySequence("F5"))
        self.action_start.triggered.connect(self.start_analyzer)

        self.action_regex_search = QAction("Поиск по РВ", self)
        self.action_regex_search.setShortcut(QKeySequence("F6"))
        self.action_regex_search.triggered.connect(self.start_regex_search)

        self.action_help = QAction("Вызов справки", self)
        self.action_help.setIcon(self._icon("help.svg", QStyle.StandardPixmap.SP_DialogHelpButton))
        self.action_help.setShortcut(QKeySequence("F1"))
        self.action_help.triggered.connect(self.show_help)

        self.action_about = QAction("О программе", self)
        self.action_about.setIcon(self._icon("about.svg", QStyle.StandardPixmap.SP_MessageBoxInformation))
        self.action_about.triggered.connect(self.show_about)

        self.action_zoom_in = QAction("Увеличить текст", self)
        self.action_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        self.action_zoom_in.triggered.connect(lambda: self._change_text_size(1))

        self.action_zoom_out = QAction("Уменьшить текст", self)
        self.action_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        self.action_zoom_out.triggered.connect(lambda: self._change_text_size(-1))

        self.action_zoom_reset = QAction("Сбросить размер текста", self)
        self.action_zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        self.action_zoom_reset.triggered.connect(self._reset_text_size)

        self.action_lang_ru = QAction("Русский", self)
        self.action_lang_ru.triggered.connect(lambda: self._switch_language("ru"))
        self.action_lang_en = QAction("English", self)
        self.action_lang_en.triggered.connect(lambda: self._switch_language("en"))

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.clear()

        self.menu_file = menu_bar.addMenu("Файл")
        self.menu_file.addAction(self.action_new)
        self.menu_file.addAction(self.action_open)
        self.menu_file.addAction(self.action_save)
        self.menu_file.addAction(self.action_save_as)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)

        self.menu_edit = menu_bar.addMenu("Правка")
        self.menu_edit.addAction(self.action_undo)
        self.menu_edit.addAction(self.action_redo)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.action_cut)
        self.menu_edit.addAction(self.action_copy)
        self.menu_edit.addAction(self.action_paste)
        self.menu_edit.addAction(self.action_delete)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.action_select_all)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.action_zoom_in)
        self.menu_edit.addAction(self.action_zoom_out)
        self.menu_edit.addAction(self.action_zoom_reset)

        self.menu_text = menu_bar.addMenu("Текст")
        for item in TEXT_MENU_ITEMS:
            action = QAction(item, self)
            action.triggered.connect(partial(self.show_text_info, item))
            self.menu_text.addAction(action)

        menu_bar.addAction(self.action_start)

        self.menu_help = menu_bar.addMenu("Справка")
        self.menu_help.addAction(self.action_help)
        self.menu_help.addAction(self.action_about)

        self.menu_language = menu_bar.addMenu("Язык")
        self.menu_language.addAction(self.action_lang_ru)
        self.menu_language.addAction(self.action_lang_en)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Панель инструментов", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(toolbar)
        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_start)
        toolbar.addAction(self.action_regex_search)
        toolbar.addSeparator()
        toolbar.addAction(self.action_undo)
        toolbar.addAction(self.action_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.action_copy)
        toolbar.addAction(self.action_cut)
        toolbar.addAction(self.action_paste)
        toolbar.addSeparator()
        toolbar.addAction(self.action_help)
        toolbar.addAction(self.action_about)

    def _new_editor(self, text: str = "", title: str = "Без имени", file_path: str | None = None) -> None:
        editor = CodeEditor()
        editor.setPlainText(text)
        editor.setProperty("file_path", file_path)
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(lambda _: self._refresh_current_tab_text())
        index = self.editor_tabs.addTab(editor, title)
        self.editor_tabs.setCurrentIndex(index)
        self._update_title()

    def _current_editor(self) -> CodeEditor | None:
        widget = self.editor_tabs.currentWidget()
        return widget if isinstance(widget, CodeEditor) else None

    def _current_file_path(self) -> str | None:
        editor = self._current_editor()
        if not editor:
            return None
        return editor.property("file_path")

    def _set_current_file_path(self, file_path: str | None) -> None:
        editor = self._current_editor()
        if editor:
            editor.setProperty("file_path", file_path)

    def _refresh_current_tab_text(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        file_path = editor.property("file_path")
        name = Path(file_path).name if file_path else "Без имени"
        mark = "*" if editor.document().isModified() else ""
        self.editor_tabs.setTabText(self.editor_tabs.currentIndex(), f"{name}{mark}")
        self._update_title()

    def _icon(self, icon_name: str, fallback: QStyle.StandardPixmap) -> QIcon:
        icon_path = self._resource_path(Path("assets") / "icons" / icon_name)
        if icon_path.exists():
            return QIcon(str(icon_path))
        return self.style().standardIcon(fallback)

    @staticmethod
    def _resource_path(relative_path: Path) -> Path:
        if getattr(sys, "_MEIPASS", None):
            return Path(sys._MEIPASS) / relative_path
        return Path(__file__).resolve().parents[2] / relative_path

    def _set_output(self, text: str) -> None:
        self.output_log.setPlainText(text)
        self.output_tabs.setCurrentWidget(self.output_log)

    @staticmethod
    def _report_code(prefix: str, text: str) -> str:
        value = sum(ord(ch) for ch in text) % 10000000000
        return f"{prefix}{value}"

    def _update_title(self) -> None:
        path = self._current_file_path()
        name = Path(path).name if path else "Без имени"
        editor = self._current_editor()
        mark = "*" if editor and editor.document().isModified() else ""
        self.setWindowTitle(f"{APP_TITLE} - {name}{mark}")
        self.statusBar().showMessage(f"Вкладок: {self.editor_tabs.count()} | Файл: {name}")

    def _ask_save_editor(self, editor: CodeEditor) -> bool:
        if not editor.document().isModified():
            return True
        result = QMessageBox.question(
            self,
            "Несохраненные изменения",
            "Документ был изменен. Сохранить изменения?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if result == QMessageBox.StandardButton.Cancel:
            return False
        if result == QMessageBox.StandardButton.Yes:
            current = self.editor_tabs.currentWidget()
            self.editor_tabs.setCurrentWidget(editor)
            ok = self.save_file()
            self.editor_tabs.setCurrentWidget(current)
            return ok
        return True

    def new_file(self) -> None:
        self._new_editor()
        self._set_output("Создан новый документ.")

    def open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Text files (*.txt);;All files (*.*)")
        if file_path:
            self._open_file_path(file_path)

    def _open_file_path(self, file_path: str) -> None:
        try:
            content = read_text_file(file_path)
        except OSError as error:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{error}")
            return
        self._new_editor(content, Path(file_path).name, file_path)
        self._set_output(f"Файл открыт:\n{file_path}")

    def save_file(self) -> bool:
        editor = self._current_editor()
        if not editor:
            return False
        path = editor.property("file_path")
        if not path:
            return self.save_file_as()
        try:
            write_text_file(path, editor.toPlainText())
        except OSError as error:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{error}")
            return False
        editor.document().setModified(False)
        self._refresh_current_tab_text()
        self._set_output(f"Файл сохранен:\n{path}")
        return True

    def save_file_as(self) -> bool:
        editor = self._current_editor()
        if not editor:
            return False
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл как", "", "Text files (*.txt);;All files (*.*)")
        if not file_path:
            return False
        self._set_current_file_path(file_path)
        return self.save_file()

    def delete_selected_text(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
            editor.setTextCursor(cursor)

    def start_analyzer(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        text = editor.toPlainText()
        self.output_errors.setRowCount(0)
        self.output_tokens.setRowCount(0)
        self.output_log.clear()  # очищаем лог
        if not text.strip():
            self._set_output("Пуск: текст пуст. Добавьте данные для анализа.")
            return

        tokens, lex_errors = scan_rust(text)
        
        # Синтаксический анализ
        syntax_errors = parse_syntax(tokens)
        
        # Объединяем ошибки
        all_errors = []
        for err in lex_errors:
            # Извлекаем фрагмент из сообщения лексической ошибки
            fragment = '?'
            if "'" in err.message:
                parts = err.message.split("'")
                if len(parts) >= 2:
                    fragment = parts[1]
            all_errors.append({
                'fragment': fragment,
                'line': err.line,
                'column': err.column,
                'message': err.message,
                'type': 'lexical'
            })
        for err in syntax_errors:
            all_errors.append({
                'fragment': err.fragment,
                'line': err.line,
                'column': err.column,
                'message': err.message,
                'type': 'syntax'
            })
        
        russian_names = {
            TokenType.KEYWORD: "Ключевое слово",
            TokenType.IDENTIFIER: "Идентификатор",
            TokenType.OPERATOR: "Оператор",
            TokenType.COLON: "Двоеточие",
            TokenType.DOT: "Точка",
            TokenType.INTEGER: "Целое число",
            TokenType.FLOAT: "Вещественное число",
            TokenType.SEPARATOR: "Разделитель",
            TokenType.END_OF_STATEMENT: "Конец оператора",
            TokenType.WHITESPACE: "Разделитель пробел",
            TokenType.ERROR: "Ошибка",
        }

        
        def visible_lexeme(lexeme: str) -> str:
           
            replacements = {
                ' ': 'пробел',
                '\t': '\\t',
                '\r': '\\r',
                '\n': '\\n',
            }
            result = []
            for ch in lexeme:
                if ch in replacements:
                    result.append(replacements[ch])
                else:
                    result.append(ch)
            return ''.join(result)

        
        for token in tokens:
            row = self.output_tokens.rowCount()
            self.output_tokens.insertRow(row)
            self.output_tokens.setItem(row, 0, QTableWidgetItem(str(token.type.value)))
            type_name = russian_names.get(token.type, token.type.name)
            self.output_tokens.setItem(row, 1, QTableWidgetItem(type_name))
            self.output_tokens.setItem(row, 2, QTableWidgetItem(visible_lexeme(token.lexeme)))
            location = f"{token.start_line}:{token.start_col}-{token.end_line}:{token.end_col}"
            self.output_tokens.setItem(row, 3, QTableWidgetItem(location))

        
        for err in all_errors:
            row = self.output_errors.rowCount()
            self.output_errors.insertRow(row)
            # Неверный фрагмент
            self.output_errors.setItem(row, 0, QTableWidgetItem(err['fragment']))
            # Местоположение
            location = f"{err['line']}:{err['column']}"
            self.output_errors.setItem(row, 1, QTableWidgetItem(location))
            # Описание ошибки
            self.output_errors.setItem(row, 2, QTableWidgetItem(err['message']))

        # Общее количество ошибок выводим в статусную строку
        total_errors = len(all_errors)
        if total_errors > 0:
            self.statusBar().showMessage(f"Найдено ошибок: {total_errors}")
        else:
            self.statusBar().showMessage("Ошибок не обнаружено")

        # Выводим общее количество ошибок в лог
        if total_errors == 0:
            self.output_log.setPlainText("Синтаксический анализ завершен успешно. Ошибок не обнаружено.")
        else:
            self.output_log.setPlainText(f"Синтаксический анализ завершен. Найдено ошибок: {total_errors}")

        # Переключение на вкладку ошибок, если есть ошибки
        if all_errors:
            self.output_tabs.setCurrentWidget(self.output_errors)
        # Иначе не менять вкладку (оставить текущую)

    def start_regex_search(self) -> None:
        """Запуск поиска по всем трём регулярным выражениям."""
        import sys
        import os
        import re
        from datetime import datetime
        
        editor = self._current_editor()
        if not editor:
            return
        text = editor.toPlainText()
        if not text.strip():
            self.output_log.setPlainText("Пуск: текст пуст. Добавьте данные для поиска.")
            QMessageBox.information(self, "Нет данных", "Нет данных для поиска.")
            return
        
        # Отладочная информация
        debug_log = []
        debug_log.append(f"=== {datetime.now().isoformat()} ===")
        debug_log.append(f"Длина текста: {len(text)}")
        debug_log.append(f"Первые 200 символов: {repr(text[:200])}")
        
        # Очищаем предыдущие результаты
        self.output_regex.setRowCount(0)
        
        searcher = RegexSearcher()
        try:
            # Ищем по всем трём шаблонам
            all_results = searcher.search_all(text)
            debug_log.append("--- Результаты по шаблонам ---")
            total_matches = 0
            for key, matches in all_results.items():
                debug_log.append(f"  {key}: {len(matches)} совпадений")
                total_matches += len(matches)
                for i, m in enumerate(matches[:3]):
                    debug_log.append(f"    {i}: '{m.substring}' на строке {m.start_line}:{m.start_char}")
        except Exception as e:
            debug_log.append(f"Ошибка при поиске: {e}")
            QMessageBox.critical(self, "Ошибка", str(e))
            self._write_debug_log(debug_log)
            return
        
        # Записать лог в файл
        self._write_debug_log(debug_log)
        
        # Собираем все совпадения в один список с указанием ключа для сортировки по позиции в тексте
        all_matches_with_key = []
        for key, matches in all_results.items():
            for match in matches:
                # Вычисляем абсолютную позицию для сортировки (примерно: start_line * 1000 + start_char)
                pos = match.start_line * 1000 + match.start_char
                all_matches_with_key.append((pos, match, key))
        
        # Сортируем по позиции
        all_matches_with_key.sort(key=lambda x: x[0])
        
        debug_log.append(f"Всего совпадений: {total_matches}")
        debug_log.append(f"Упорядоченных записей: {len(all_matches_with_key)}")
        
        # Заполняем таблицу
        rows_added = 0
        error_messages = []
        for pos, match, key in all_matches_with_key:
            row = self.output_regex.rowCount()
            try:
                self.output_regex.insertRow(row)
                self.output_regex.setItem(row, 0, QTableWidgetItem(match.substring))
                position = f"{match.start_line}:{match.start_char}"
                self.output_regex.setItem(row, 1, QTableWidgetItem(position))
                self.output_regex.setItem(row, 2, QTableWidgetItem(str(match.length)))
                self.output_regex.setItem(row, 3, QTableWidgetItem(searcher.get_pattern_description(key)))
                rows_added += 1
            except Exception as e:
                error_msg = f"Ошибка при добавлении строки {row}: {e}"
                debug_log.append(error_msg)
                error_messages.append(error_msg)
        
        debug_log.append(f"Добавлено строк в таблицу: {rows_added}")
        
        # Диагностика: если совпадения есть, но строк не добавлено
        if rows_added == 0 and total_matches > 0:
            warning = "ВНИМАНИЕ: Совпадения найдены, но таблица осталась пустой. Возможно, ошибка при добавлении строк."
            debug_log.append(warning)
            if error_messages:
                debug_log.extend(["Ошибки добавления:", *error_messages])
        
        # Если есть ошибки добавления, добавить их в лог
        if error_messages:
            debug_log.append("--- Ошибки добавления строк ---")
            debug_log.extend(error_messages)
        
        # Записать обновлённый лог (дополненный)
        self._write_debug_log(debug_log)
        
        # Переключаемся на вкладку результатов поиска
        self.output_tabs.setCurrentWidget(self.output_regex)
        
        # Выводим количество найденных совпадений в статусную строку и лог (без переключения вкладки)
        if total_matches == 0:
            self.statusBar().showMessage("Поиск завершен. Совпадений не найдено.")
            self.output_log.setPlainText("Поиск по регулярному выражению завершен. Совпадений не найдено.")
        else:
            status_msg = f"Найдено совпадений: {total_matches}"
            log_msg = f"Поиск по регулярному выражению завершен. Найдено совпадений: {total_matches}"
            if rows_added != total_matches:
                status_msg += f" (добавлено {rows_added})"
                log_msg += f", добавлено строк: {rows_added}"
                if error_messages:
                    log_msg += f". Произошло {len(error_messages)} ошибок добавления."
            self.statusBar().showMessage(status_msg)
            self.output_log.setPlainText(log_msg)

    def _write_debug_log(self, lines: list[str]) -> None:
        """Записать отладочный лог в файл."""
        import os
        log_path = "debug_regex.log"
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n\n')
        except Exception as e:
            print(f"Не удалось записать лог: {e}")

    def _tbl_item(self, text: str):
        from PySide6.QtWidgets import QTableWidgetItem

        return QTableWidgetItem(text)

    def _jump_to_error(self, row: int, _col: int) -> None:
        editor = self._current_editor()
        if not editor:
            return
        location_item = self.output_errors.item(row, 1)  # столбец "Местоположение"
        if not location_item:
            return
        location = location_item.text()
        # Ожидаемый формат: "строка:позиция"
        parts = location.split(':')
        if len(parts) != 2:
            return
        try:
            line = max(1, int(parts[0]))
            pos = max(1, int(parts[1]))
        except ValueError:
            return
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, line - 1)
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, pos - 1)
        editor.setTextCursor(cursor)
        editor.setFocus()

    def _jump_to_token(self, row: int, _col: int) -> None:
        editor = self._current_editor()
        if not editor:
            return
        location_item = self.output_tokens.item(row, 3)
        if not location_item:
            return
        location = location_item.text()
        import re
        match = re.match(r"(\d+):(\d+)-(\d+):(\d+)", location)
        if not match:
            return
        start_line, start_col, end_line, end_col = map(int, match.groups())
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, start_line - 1)
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, start_col - 1)
       
        end_cursor = editor.textCursor()
        end_cursor.movePosition(cursor.MoveOperation.Start)
        end_cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, end_line - 1)
        end_cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, end_col - 1)
        cursor.setPosition(end_cursor.position(), cursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        editor.setFocus()

    def _jump_to_regex_match(self, row: int, _col: int) -> None:
        """Переход к найденной подстроке и её выделение."""
        editor = self._current_editor()
        if not editor:
            return
        # Получаем данные из таблицы
        substring_item = self.output_regex.item(row, 0)
        position_item = self.output_regex.item(row, 1)
        if not substring_item or not position_item:
            return
        substring = substring_item.text()
        position = position_item.text()  # формат "строка:символ"
        parts = position.split(':')
        if len(parts) != 2:
            return
        try:
            line = max(1, int(parts[0]))
            char = max(1, int(parts[1]))
        except ValueError:
            return
        
        # Вычисляем позицию начала и конца подстроки
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, line - 1)
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, char - 1)
        start_pos = cursor.position()
        end_pos = start_pos + len(substring)
        
        # Выделяем подстроку
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, cursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        editor.setFocus()
        
        # Прокручиваем редактор к выделению
        editor.ensureCursorVisible()

    def show_help(self) -> None:
        QMessageBox.information(self, "Справка", HELP_TEXT)

    def show_about(self) -> None:
        QMessageBox.information(self, "О программе", ABOUT_TEXT)

    def show_text_info(self, item_name: str) -> None:
        if item_name == "Тестовый пример":
            # Создаем список строк для диалога выбора
            items = [f"{i+1}. {desc}" for i, (code, desc) in enumerate(TEST_EXAMPLES)]
            item, ok = QInputDialog.getItem(
                self,
                "Выбор тестового примера",
                "Выберите пример для загрузки в редактор:",
                items,
                0,  # текущий индекс
                False  # не редактируемый
            )
            if not ok or not item:
                return
            # Извлекаем индекс
            idx = items.index(item)
            code, desc = TEST_EXAMPLES[idx]
            # Создаем новую вкладку с примером
            self._new_editor(code, f"Пример {idx+1}: {desc}")
            # Запускаем анализ
            self.start_analyzer()
        else:
            QMessageBox.information(self, item_name, TEXT_MENU_HINTS[item_name])

    def close_editor_tab(self, index: int) -> None:
        widget = self.editor_tabs.widget(index)
        if isinstance(widget, CodeEditor) and not self._ask_save_editor(widget):
            return
        self.editor_tabs.removeTab(index)
        if self.editor_tabs.count() == 0:
            self.new_file()
        self._update_title()

    def _change_text_size(self, step: int) -> None:
        editor = self._current_editor()
        if editor:
            editor.zoomIn(step)
        self.output_log.zoomIn(step)

    def _reset_text_size(self) -> None:
        for widget in [self._current_editor(), self.output_log]:
            if widget:
                font = widget.font()
                font.setPointSize(10)
                widget.setFont(font)

    def _switch_language(self, lang: str) -> None:
        self.language = lang
        if lang == "en":
            self.menu_file.setTitle("File")
            self.menu_edit.setTitle("Edit")
            self.menu_text.setTitle("Text")
            self.menu_help.setTitle("Help")
            self.menu_language.setTitle("Language")
            self.statusBar().showMessage("Language switched to English", 3000)
        else:
            self.menu_file.setTitle("Файл")
            self.menu_edit.setTitle("Правка")
            self.menu_text.setTitle("Текст")
            self.menu_help.setTitle("Справка")
            self.menu_language.setTitle("Язык")
            self.statusBar().showMessage("Язык переключен на русский", 3000)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local and Path(local).is_file():
                self._open_file_path(local)
        event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent) -> None:
        for i in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(i)
            if isinstance(editor, CodeEditor) and not self._ask_save_editor(editor):
                event.ignore()
                return
        event.accept()
