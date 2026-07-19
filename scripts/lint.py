#!/usr/bin/env python3
"""Детерминированный линтер AI-слопа для humanizer-ru.

Использование:
    python3 scripts/lint.py file.md      # или stdin: python3 scripts/lint.py < file.md
    python3 scripts/lint.py --self-test

ERROR  = жёсткие запреты SKILL.md (гейт: exit 1, текст не готов).
WARN   = маркеры паттернов (информация для судейского прохода, exit 0).
Линт гоняется ТОЛЬКО по чистовому тексту - без changelog и цитат «до».
"""
import re
import sys

# --- жёсткие запреты (номера паттернов из references/patterns.md) ---
ERRORS = [
    ("23 длинное тире", re.compile(r"[—–]")),
    ("23 мат-знаки", re.compile(r"(?:[≈≥≤≠±⇒←→]|\s[=><&+]\s|\d\+(?!\d)|\bvs\.?\b)")),
    ("13 негативный параллелизм", re.compile(
        r"[Нн]е (?:просто|только)\b(?:[^.!?\n]{0,80}?\bно и\b)?|[Рр]ечь идёт не только|"
        r"[Нн]ет [^,.!?\n]{1,40}, нет ")),
    ("27 рубленый драматизм", re.compile(r"(?:Без|Ноль) [^.!?\n]{1,35}[.!] (?:Без|Ноль) ")),
]

# --- маркеры для судейского прохода (кластеры решают, не одиночные хиты) ---
WARN_PHRASES = [
    # 3 избегание «это»
    "представляет собой", "выступает в роли", "служит основой", "знаменует собой",
    # 6 AI-словарь (стемы ловят словоформы)
    "ключев", "важнейш", "знаменует", "демонстрир", "способств", "подчёркива",
    "свидетельств", "неуклонно",
    # 10 размытые атрибуции
    "по мнению экспертов", "аналитики отмечают", "исследователи утверждают",
    # 11 шаблонные переходы
    "важно отметить", "следует подчеркнуть", "необходимо учитывать",
    "стоит обратить внимание", "нельзя не упомянуть",
    # 12 вызовы и перспективы
    "сталкивается с рядом вызовов", "несмотря на эти вызовы",
    # 17-18 подобострастие и артефакты чатбота
    "отличный вопрос", "надеюсь, это поможет", "надеюсь, было полезно",
    "дайте знать", "буду рад помочь",
    # 20 позитивные заключения
    "будущее выглядит ярким", "впереди захватывающие времена", "продолжает процветать",
    # 22 стоп-слова
    "в современном мире", "на сегодняшний день", "в настоящее время", "как известно",
    "не секрет, что", "ни для кого не секрет", "каждый из нас",
    # 25 псевдоглубина
    "по сути", "если копнуть глубже", "глубинная проблема", "настоящий вопрос в том",
    "в конечном счёте",
    # 26 анонсы
    "давайте разберёмся", "погрузимся в", "вот что нужно знать", "без лишних слов",
    # 29 фальшивая доверительность
    "скажу прямо", "давайте начистоту", "вот в чём штука", "если по-честному",
    # 31 резюме
    "подводя итог", "в заключение", "резюмируя",
    # 32 спекуляции
    "широко не задокументирован", "предположительно",
]
WARN_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")

STRIP = re.compile(r"```.*?```|`[^`\n]+`|https?://\S+", re.S)  # код и URL не проза


def lint(text):
    findings = []  # (kind, line_no, rule, excerpt)
    clean = STRIP.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    lines = clean.splitlines()
    for i, line in enumerate(lines, 1):
        scan = re.sub(r"^\s*[>+*]\s", "  ", line)  # markdown-маркеры не прозаические знаки
        for rule, rx in ERRORS:
            for m in rx.finditer(scan):
                ctx = scan[max(0, m.start() - 25):m.end() + 25].strip()
                findings.append(("ERROR", i, rule, ctx))
        low = scan.lower()
        for phrase in WARN_PHRASES:
            if phrase in low:
                findings.append(("WARN", i, phrase, scan.strip()[:70]))
        if WARN_EMOJI.search(scan):
            findings.append(("WARN", i, "21 эмодзи", scan.strip()[:70]))
    return findings


def self_test():
    bad = "Это не просто курс — это экосистема. Скорость > идеальности. Без кода. Без настроек. Итог ≈ 5+ часов, джуны vs сеньоры."
    kinds = [f[2] for f in lint(bad) if f[0] == "ERROR"]
    assert any("13" in k for k in kinds), kinds
    assert any("тире" in k for k in kinds), kinds
    assert any("мат-знаки" in k for k in kinds), kinds
    assert any("27" in k for k in kinds), kinds
    ok = "Обычный текст - с коротким тире, без слопа. Цифры 12 и 87 на месте.\n> цитата\n+ пункт списка"
    assert not [f for f in lint(ok) if f[0] == "ERROR"], lint(ok)
    warn = "Важно отметить, что по сути будущее выглядит ярким."
    assert len([f for f in lint(warn) if f[0] == "WARN"]) >= 3
    print("self-test: OK")


def main():
    if "--self-test" in sys.argv:
        return self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    text = open(args[0], encoding="utf-8").read() if args else sys.stdin.read()
    findings = lint(text)
    errors = [f for f in findings if f[0] == "ERROR"]
    for kind, line_no, rule, ctx in findings:
        print(f"{kind} строка {line_no}: [{rule}] {ctx}")
    print(f"\nитого: {len(errors)} errors, {len(findings) - len(errors)} warnings")
    if errors:
        print("ГЕЙТ НЕ ПРОЙДЕН - текст не готов, чини errors и запускай снова.")
        sys.exit(1)
    print("гейт пройден: жёстких запретов нет. Warnings оцени кластерами.")


if __name__ == "__main__":
    main()
