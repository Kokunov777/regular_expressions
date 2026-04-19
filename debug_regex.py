import sys
sys.path.insert(0, '.')
from src.core.regex_search import RegexSearcher

with open('test_samples.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print("Текст загружен, длина:", len(text))
searcher = RegexSearcher()
print("Ключи шаблонов:", searcher.get_pattern_keys())

for key in searcher.get_pattern_keys():
    print(f"\n--- Поиск по ключу: {key} ---")
    try:
        matches = searcher.search(text, key)
        print(f"Найдено совпадений: {len(matches)}")
        for i, m in enumerate(matches[:5]):
            print(f"  {i+1}. '{m.substring}' строка {m.start_line}:{m.start_char}")
    except Exception as e:
        print(f"Ошибка: {e}")