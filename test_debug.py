#!/usr/bin/env python3
"""
Запускает приложение, загружает тестовый файл и выполняет поиск по каждому шаблону,
чтобы проверить отладочный вывод.
"""
import sys
import os
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from src.ui.main_window import MainWindow

def test():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Загружаем тестовый файл
    with open('test_samples.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    editor = window._current_editor()
    if not editor:
        print("Ошибка: редактор не найден")
        return
    editor.setPlainText(content)
    print("Текст загружен")
    
    # Выполняем поиск для каждого шаблона
    def run_search(index):
        if index >= window.regex_combo.count():
            QTimer.singleShot(500, app.quit)
            return
        window.regex_combo.setCurrentIndex(index)
        window.start_regex_search()
        QTimer.singleShot(300, lambda: run_search(index + 1))
    
    QTimer.singleShot(500, lambda: run_search(0))
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test()