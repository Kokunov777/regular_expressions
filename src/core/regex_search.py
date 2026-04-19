"""
Модуль поиска подстрок с использованием регулярных выражений.
Предоставляет функции для поиска годов 2000-2010, номеров карт Maestro и IP-адресов с маской.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class MatchResult:
    """Результат совпадения регулярного выражения."""
    substring: str          # найденная подстрока
    start_line: int        # номер строки (1-индексированный)
    start_char: int        # номер символа в строке (1-индексированный)
    length: int            # длина подстроки в символах
    end_line: int          # номер строки конца (для информации)
    end_char: int          # номер символа конца


class RegexSearcher:
    """Класс для поиска подстрок по регулярным выражениям."""
    
    # Регулярные выражения для вариантов
    PATTERNS = {
        "years_2000_2010": r'\b(200[0-9]|2010)\b',
        "maestro_card": r'\b(50[0-9]{10,17}|5[6-8][0-9]{10,17}|6[0-9]{11,18})\b',
        "ip_with_mask": r'\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/([0-9]|[12][0-9]|3[0-2])\b',
    }
    
    # Описания для отображения
    DESCRIPTIONS = {
        "years_2000_2010": "Годы между 2000 и 2010",
        "maestro_card": "Номера карт Maestro",
        "ip_with_mask": "IP-адрес (v4) с маской подсети",
    }
    
    def __init__(self):
        self.compiled = {key: re.compile(pattern) for key, pattern in self.PATTERNS.items()}
    
    def search(self, text: str, pattern_key: str) -> List[MatchResult]:
        """
        Ищет все вхождения заданного регулярного выражения в тексте.
        
        Args:
            text: исходный текст
            pattern_key: ключ из PATTERNS (years_2000_2010, maestro_card, ip_with_mask)
        
        Returns:
            Список объектов MatchResult, отсортированных по позиции в тексте.
        
        Raises:
            ValueError: если pattern_key неизвестен
        """
        if pattern_key not in self.compiled:
            raise ValueError(f"Неизвестный ключ шаблона: {pattern_key}. Доступные: {list(self.PATTERNS.keys())}")
        
        regex = self.compiled[pattern_key]
        lines = text.splitlines(keepends=True)
        results = []
        
        # Для вычисления абсолютной позиции в тексте
        current_pos = 0
        
        for line_idx, line in enumerate(lines, start=1):
            for match in regex.finditer(line):
                start = match.start()
                end = match.end()
                substring = match.group()
                
                # Абсолютные позиции в тексте
                abs_start = current_pos + start
                abs_end = current_pos + end
                
                # Номер символа в строке (1-индексированный)
                char_in_line = start + 1
                
                results.append(MatchResult(
                    substring=substring,
                    start_line=line_idx,
                    start_char=char_in_line,
                    length=len(substring),
                    end_line=line_idx,
                    end_char=start + len(substring)  # конец в той же строке
                ))
            
            current_pos += len(line)
        
        return results
    
    def search_all(self, text: str) -> dict:
        """
        Выполняет поиск по всем трём шаблонам и возвращает словарь результатов.
        
        Returns:
            Словарь {pattern_key: [MatchResult, ...]}
        """
        return {key: self.search(text, key) for key in self.PATTERNS.keys()}
    
    @classmethod
    def get_pattern_keys(cls) -> List[str]:
        """Возвращает список ключей шаблонов."""
        return list(cls.PATTERNS.keys())
    
    @classmethod
    def get_pattern_description(cls, key: str) -> str:
        """Возвращает описание шаблона по ключу."""
        return cls.DESCRIPTIONS.get(key, "Неизвестный шаблон")


def find_years_2000_2010(text: str) -> List[MatchResult]:
    """Утилитарная функция: поиск годов 2000-2010."""
    searcher = RegexSearcher()
    return searcher.search(text, "years_2000_2010")


def find_maestro_cards(text: str) -> List[MatchResult]:
    """Утилитарная функция: поиск номеров карт Maestro."""
    searcher = RegexSearcher()
    return searcher.search(text, "maestro_card")


def find_ip_with_mask(text: str) -> List[MatchResult]:
    """Утилитарная функция: поиск IP-адресов с маской."""
    searcher = RegexSearcher()
    return searcher.search(text, "ip_with_mask")


if __name__ == "__main__":
    # Пример использования
    sample_text = """
    В 2005 году я получил карту Maestro 5012345678901234.
    Мой IP-адрес 192.168.1.1/24, а также 10.0.0.1/8.
    Годы: 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010.
    Неправильные: 1999, 2011, 20011.
    Другой номер карты: 561234567890123456.
    IP с ошибкой: 256.0.0.1/24.
    """
    
    searcher = RegexSearcher()
    print("=== Поиск годов 2000-2010 ===")
    years = searcher.search(sample_text, "years_2000_2010")
    for m in years:
        print(f"  {m.substring} на строке {m.start_line}:{m.start_char}")
    
    print("\n=== Поиск карт Maestro ===")
    cards = searcher.search(sample_text, "maestro_card")
    for m in cards:
        print(f"  {m.substring} на строке {m.start_line}:{m.start_char}")
    
    print("\n=== Поиск IP с маской ===")
    ips = searcher.search(sample_text, "ip_with_mask")
    for m in ips:
        print(f"  {m.substring} на строке {m.start_line}:{m.start_char}")
    
    print("\n=== Статистика ===")
    all_results = searcher.search_all(sample_text)
    for key, matches in all_results.items():
        print(f"{searcher.get_pattern_description(key)}: найдено {len(matches)}")