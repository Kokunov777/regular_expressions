#!/usr/bin/env python3
"""
Скрипт для тестирования поиска по регулярным выражениям через UI.
Загружает тестовый файл в редактор и выполняет поиск для каждого шаблона.
"""
import sys
import os
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication, QMessageBox
from src.ui.main_window import MainWindow
from src.core.regex_search import RegexSearcher

def test():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Загружаем тестовый файл в редактор
    test_file = "test_samples.txt"
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # Получаем текущий редактор (первая вкладка)
        editor = window._current_editor()
        if editor:
            editor.setPlainText(content)
            print(f"Загружен тестовый файл, длина текста: {len(content)}")
        else:
            print("Нет редактора")
    else:
        print(f"Файл {test_file} не найден")
    
    # Выполняем поиск для каждого шаблона
    searcher = RegexSearcher()
    text = content if 'content' in locals() else ""
    for key in ["years_2000_2010", "maestro_card", "ip_with_mask"]:
        matches = searcher.search(text, key)
        print(f"Шаблон {key}: найдено {len(matches)} совпадений")
        for m in matches[:5]:
            print(f"  {m.substring} на строке {m.start_line}:{m.start_char}")
    
    # Запускаем цикл обработки событий на короткое время, затем закрываем
    timer = window.startTimer(2000)  # таймер на 2 секунды
    def on_timeout():
        window.killTimer(timer)
        window.close()
        app.quit()
    window.timerEvent = lambda e: on_timeout()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test()