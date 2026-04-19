import re

with open('test_samples.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print("=== Поиск годов ===")
years_pattern = r'\b(200[0-9]|2010)\b'
years_matches = list(re.finditer(years_pattern, text))
for m in years_matches:
    print(f"  '{m.group()}' at {m.start()}-{m.end()}")

print("\n=== Поиск Maestro ===")
maestro_pattern = r'\b(50[0-9]{10,17}|5[6-8][0-9]{10,17}|6[0-9]{11,18})\b'
maestro_matches = list(re.finditer(maestro_pattern, text))
for m in maestro_matches:
    print(f"  '{m.group()}' at {m.start()}-{m.end()}")

print("\n=== Поиск IP с маской ===")
ip_pattern = r'\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/([0-9]|[12][0-9]|3[0-2])\b'
ip_matches = list(re.finditer(ip_pattern, text))
for m in ip_matches:
    print(f"  '{m.group()}' at {m.start()}-{m.end()}")

print("\n=== Статистика ===")
print(f"Годы: {len(years_matches)}")
print(f"Maestro: {len(maestro_matches)}")
print(f"IP: {len(ip_matches)}")