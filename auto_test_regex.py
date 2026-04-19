#!/usr/bin/env python3
"""
Автоматический тест поиска по регулярным выражениям.
Запускает приложение, загружает тестовый файл, выполняет поиск для каждого шаблона
и проверяет, что таблица заполняется.
"""
import sys
import os
import time
from PySide6.QtWidgets import QApplication, QTableWidgetItem
from PySide6.QtCore import QTimer
sys.path.insert(0, '.')

from src.ui.main_window import MainWindow

def test():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Загружаем тестовый файл
    test_file = "test_samples.txt"
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    editor = window._current_editor()
    if not editor:
        print("Ошибка: редактор не найден")
        return
    editor.setPlainText(content)
    print(f"Загружен текст длиной {len(content)} символов")
    
    # Функция для выполнения поиска и проверки результатов
    def run_search(pattern_key_index):
        if pattern_key_index >= window.regex_combo.count():
            # Все шаблоны проверены, закрываем приложение
            QTimer.singleShot(500, app.quit)
            return
        
        # Устанавливаем комбобокс
        window.regex_combo.setCurrentIndex(pattern_key_index)
        key = window.regex_combo.currentData()
        print(f"\n=== Тестирование шаблона: {key} ===")
        
        # Вызываем поиск
        window.start_regex_search()
        
        # Даём время на обработку
        QTimer.singleShot(300, lambda: check_results(key, pattern_key_index))
    
    def check_results(key, pattern_key_index):
        # Проверяем количество строк в таблице
        rows = window.output_regex.rowCount()
        print(f"  Строк в таблице: {rows}")
        if rows == 0:
            print("  ВНИМАНИЕ: таблица пуста!")
            # Выведем отладочную информацию из stderr (уже выведена)
        else:
            for r in range(min(rows, 3)):
                item = window.output_regex.item(r, 0)
                if item:
                    print(f"  Строка {r}: {item.text()}")
        
        # Переходим к следующему шаблону
        QTimer.singleShot(300, lambda: run_search(pattern_key_index + 1))
    
    # Запускаем первый поиск через короткую задержку
    QTimer.singleShot(500, lambda: run_search(0))
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test()