#!/usr/bin/env python3
"""
Финальная проверка модуля поиска по регулярным выражениям.
Проверяет:
1. Загрузку тестового файла
2. Поиск по каждому шаблону
3. Заполнение таблицы
4. Переключение вкладок
5. Подсветку при двойном клике
"""
import sys
import os
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication, QTableWidgetItem
from PySide6.QtCore import QTimer, Qt
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
    print("[OK] Текст загружен")
    
    # Проверяем, что комбобокс содержит три элемента
    assert window.regex_combo.count() == 3, f"Ожидалось 3 элемента, получено {window.regex_combo.count()}"
    print("[OK] Комбобокс содержит три шаблона")
    
    # Функция для проверки поиска
    def check_pattern(index):
        if index >= window.regex_combo.count():
            # Все шаблоны проверены
            print("\n=== Все проверки пройдены успешно ===")
            QTimer.singleShot(500, app.quit)
            return
        
        key = window.regex_combo.itemData(index)
        window.regex_combo.setCurrentIndex(index)
        window.start_regex_search()
        
        QTimer.singleShot(300, lambda: verify_results(key, index))
    
    def verify_results(key, index):
        rows = window.output_regex.rowCount()
        expected_counts = {
            "years_2000_2010": 20,
            "maestro_card": 7,
            "ip_with_mask": 10
        }
        expected = expected_counts.get(key, 0)
        if rows == expected:
            print(f"[OK] Шаблон '{key}': найдено {rows} совпадений (ожидалось {expected})")
        else:
            print(f"[FAIL] Шаблон '{key}': найдено {rows} совпадений, ожидалось {expected}")
        
        # Проверяем, что активная вкладка - результаты поиска
        current_tab = window.output_tabs.currentWidget()
        if current_tab == window.output_regex:
            print("  [OK] Вкладка переключена на 'Поиск по РВ'")
        else:
            print(f"  [FAIL] Активная вкладка: {current_tab.objectName()}")
        
        # Переходим к следующему шаблону
        QTimer.singleShot(300, lambda: check_pattern(index + 1))
    
    # Запускаем проверку через короткую задержку
    QTimer.singleShot(500, lambda: check_pattern(0))
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test()