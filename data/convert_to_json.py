import json

WORDS_DATA = {}

with open('words_clean.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        parts = line.split('\t')
        if len(parts) < 3:
            continue

        hanzi = parts[0].strip()
        pinyin = parts[1].strip()
        translation = parts[2].strip()

        WORDS_DATA[hanzi] = {
            'pinyin': pinyin,
            'translation': translation
        }

with open('words.json', 'w',encoding='utf-8') as f:
    json.dump(WORDS_DATA, f, ensure_ascii=False, indent=2)

print(f"Готово! Обработано {len(WORDS_DATA)} слов. Результат в файле words.json")