#!/usr/bin/env python3
"""Тестирование регулярных выражений для лабораторной работы 4."""

import re

# Регулярные выражения
REGEX_YEARS = r'\b(200[0-9]|2010)\b'
REGEX_MAESTRO = r'\b(50[0-9]{10,17}|5[6-8][0-9]{10,17}|6[0-9]{11,18})\b'
REGEX_IP_MASK = r'\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/([0-9]|[12][0-9]|3[0-2])\b'

def test_regex(pattern, test_cases, description):
    print(f"\n=== Testing {description} ===")
    print(f"Regex: {pattern}")
    compiled = re.compile(pattern)
    for text, expected in test_cases:
        match = compiled.search(text)
        found = match is not None
        status = "PASS" if found == expected else "FAIL"
        print(f"{status} '{text}' -> {'found' if found else 'not found'} (expected {'found' if expected else 'not found'})")
        if found and match:
            print(f"    Match: '{match.group()}' position {match.start()}")

# Тестовые данные для годов
years_cases = [
    ("2000", True),
    ("2005", True),
    ("2010", True),
    ("2011", False),
    ("1999", False),
    ("200", False),
    ("20005", False),  # часть большего числа
    ("год 2005 и 2009", True),
    ("2005-2009", True),
    (" 2007 ", True),
    ("2000-2010", True),  # содержит оба
]

# Тестовые данные для Maestro карт
maestro_cases = [
    ("5012345678901234", True),  # 16 цифр, начинается с 50
    ("561234567890123456", True),  # 18 цифр
    ("571234567890123", True),  # 15 цифр
    ("58123456789012345", True),  # 17 цифр
    ("612345678901234567", True),  # 18 цифр, начинается с 6
    ("501234567890", True),  # 12 цифр
    ("4912345678901234", False),  # Visa
    ("5112345678901234", False),  # MasterCard
    ("561234567890", True),  # 12 цифр
    ("5612345678901234567", True),  # 19 цифр
    ("56123456789012345678", False),  # 20 цифр - слишком много
    ("56 1234567890123456", False),  # пробел
]

# Тестовые данные для IP с маской
ip_mask_cases = [
    ("192.168.1.1/24", True),
    ("10.0.0.1/8", True),
    ("255.255.255.255/32", True),
    ("0.0.0.0/0", True),
    ("256.0.0.1/24", False),  # октет >255
    ("192.168.1.1/33", False),  # маска >32
    ("192.168.1.1/", False),
    ("192.168.1/24", False),
    ("192.168.1.1.1/24", False),
    (" 192.168.1.1/24 ", True),
    ("IP: 10.10.10.10/16", True),
    ("192.168.1.1/24 и 10.0.0.1/8", True),
]

if __name__ == "__main__":
    test_regex(REGEX_YEARS, years_cases, "годы 2000-2010")
    test_regex(REGEX_MAESTRO, maestro_cases, "номера карт Maestro")
    test_regex(REGEX_IP_MASK, ip_mask_cases, "IP-адрес с маской")
    print("\n=== Все тесты завершены ===")