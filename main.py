import random
import math
import re
from collections import Counter
import os

# ==========================================
# 1. БІОМЕХАНІЧНА КОНФІГУРАЦІЯ (CORNE 42)
# ==========================================
# Тепер кожна клавіша має "Фізіологічну вартість" (від 1 до 10).
# 1-2: Ідеально (Вказівний/Середній на домашньому ряду)
# 3-4: Добре (Верхній ряд для довгих пальців)
# 5-6: Терпимо (Мізинець домашній, Вказівний нижній)
# 7-8: Важко (Внутрішня колонка - розтяжка)
# 9-10: Біль (Мізинець верх/низ)

# Формат: (ID_Пальця, Фізіологічна_Вартість)
# Пальці ліворуч: 0(Мізинець), 1(Підмізинний), 2(Середній), 3(Вказівний), 4(Внутрішній)
# Пальці праворуч: 5(Внутрішній), 6(Вказівний), 7(Середній), 8(Підмізинний), 9(Мізинець)

SLOTS = [
    # --- ЛІВА РУКА (Верхній ряд) ---
    (0, 8), (1, 4), (2, 2), (3, 3), (4, 7),
    # --- ЛІВА РУКА (Домашній ряд) ---
    (0, 5), (1, 3), (2, 1), (3, 1), (4, 6),
    # --- ЛІВА РУКА (Нижній ряд) ---
    (0, 10), (1, 6), (2, 5), (3, 4), (4, 8),

    # --- ПРАВА РУКА (Верхній ряд) ---
    (5, 7), (6, 3), (7, 2), (8, 4), (9, 8), (9, 10),  # У правій 6 колонок (крайня для спецсимволів)
    # --- ПРАВА РУКА (Домашній ряд) ---
    (5, 6), (6, 1), (7, 1), (8, 3), (9, 5), (9, 8),
    # --- ПРАВА РУКА (Нижній ряд) ---
    (5, 8), (6, 4), (7, 5), (8, 6), (9, 10), (9, 10)
]

# Ваги алгоритму (Людська фізіологія)
SFB_PENALTY = 100.0  # Штраф за один палець (Підвищено! Люди ненавидять SFB)
EFFORT_WEIGHT = 2.0  # Вага втоми пальця (щоб часті літери йшли на сильні пальці)
ALTERNATION_BONUS = 3.0  # Бонус за чергування рук (Пінг-понг)
INWARD_ROLL_BONUS = 5.0  # Бонус за рух від мізинця до вказівного (зручно)
OUTWARD_ROLL_BONUS = 1.0  # Бонус за рух від вказівного до мізинця (нормально)


# ==========================================
# 2. АНАЛІЗАТОР ТЕКСТУ (ДЛЯ ВЕЛИКИХ ДАНИХ)
# ==========================================
def load_corpus(directory="corpus_texts"):
    print(f"Шукаю текстові файли у папці '{directory}'...")
    char_counts = Counter()
    bigram_counts = Counter()
    total_chars = 0

    if os.path.exists(directory) and os.path.isdir(directory):
        files_found = False
        for filename in os.listdir(directory):
            if filename.endswith(".txt"):
                files_found = True
                filepath = os.path.join(directory, filename)
                print(f"  - Зчитування файлу: {filename} ...")
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        prev_char = ""
                        for line in f:
                            clean_line = re.sub(r'[^абвгдеєжзиіїйклмнопрстуфхцчшщьюяґ]', '', line.lower())
                            if not clean_line: continue

                            char_counts.update(clean_line)
                            total_chars += len(clean_line)

                            if len(clean_line) > 1:
                                bigram_counts.update(zip(clean_line, clean_line[1:]))
                            if prev_char:
                                bigram_counts.update([(prev_char, clean_line[0])])
                            prev_char = clean_line[-1]
                except Exception as e:
                    print(f"    [!] Помилка: {e}")
        if not files_found:
            print(f"  [!] У папці '{directory}' не знайдено .txt файлів.")
    else:
        os.makedirs(directory)
        print(f"  Створено папку '{directory}'. Покладіть туди тексти.")

    if total_chars == 0:
        print("Використовую базовий текст...")
        demo_text = "це демонстраційний текст для алгоритму абвгґдеєжзиіїйклмнопрстуфхцчшщьюя" * 100
        demo_text = re.sub(r'[^абвгдеєжзиіїйклмнопрстуфхцчшщьюяґ]', '', demo_text)
        char_counts.update(demo_text)
        bigram_counts.update(zip(demo_text, demo_text[1:]))
        total_chars = len(demo_text)

    print(f"\nОброблено {total_chars:,} символів.")
    return char_counts, bigram_counts


# ==========================================
# 3. БІОМЕХАНІЧНИЙ СКОРИНГ (ОЦІНКА)
# ==========================================
def calculate_score(layout, char_counts, bigram_counts):
    score = 0.0

    # 1. Фізична втома (часті літери на слабких пальцях дають величезний штраф)
    for i, char in enumerate(layout):
        finger, effort = SLOTS[i]
        score += char_counts[char] * effort * EFFORT_WEIGHT

    # 2. Аналіз рухів між двома літерами
    for (c1, c2), count in bigram_counts.items():
        if c1 == c2: continue

        pos1, pos2 = layout.index(c1), layout.index(c2)
        finger1, finger2 = SLOTS[pos1][0], SLOTS[pos2][0]

        hand1 = 0 if finger1 <= 4 else 1
        hand2 = 0 if finger2 <= 4 else 1

        # Конфлікт одного пальця (SFB)
        if finger1 == finger2:
            score += count * SFB_PENALTY

        # Чергування рук (Пінг-понг)
        elif hand1 != hand2:
            score -= count * ALTERNATION_BONUS

        # Роли (Перекати на одній руці)
        else:
            # Ліва рука: 0(Мізинець) -> 4(Вказівний-внутр). Рух вгору по цифрах = Внутрішній рол
            if hand1 == 0:
                if finger2 > finger1:
                    score -= count * INWARD_ROLL_BONUS
                else:
                    score -= count * OUTWARD_ROLL_BONUS
            # Права рука: 5(Вказівний-внутр) -> 9(Мізинець). Рух вниз по цифрах = Внутрішній рол
            else:
                if finger2 < finger1:
                    score -= count * INWARD_ROLL_BONUS
                else:
                    score -= count * OUTWARD_ROLL_BONUS

    return score


# ==========================================
# 4. СИМУЛЬОВАНИЙ ВІДПАЛ
# ==========================================
def optimize_layout(char_counts, bigram_counts, iterations=100000):
    alphabet = list("абвгдеєжзиіїйклмнопрстуфхцчшщьюяґ")
    current_layout = alphabet[:]
    random.shuffle(current_layout)

    current_score = calculate_score(current_layout, char_counts, bigram_counts)
    best_layout = current_layout[:]
    best_score = current_score

    initial_temp = 1000.0
    final_temp = 0.1
    cooling_rate = (final_temp / initial_temp) ** (1.0 / iterations)
    temp = initial_temp

    print(f"Починаємо оптимізацію ({iterations:,} ітерацій)...")

    for i in range(iterations):
        idx1, idx2 = random.sample(range(33), 2)
        new_layout = current_layout[:]
        new_layout[idx1], new_layout[idx2] = new_layout[idx2], new_layout[idx1]

        new_score = calculate_score(new_layout, char_counts, bigram_counts)

        if new_score < current_score:
            current_layout = new_layout
            current_score = new_score
            if new_score < best_score:
                best_layout = new_layout[:]
                best_score = new_score
        else:
            probability = math.exp((current_score - new_score) / temp)
            if random.random() < probability:
                current_layout = new_layout
                current_score = new_score

        temp *= cooling_rate
        if i % 10000 == 0:
            print(f"Прогрес: {i:,} / {iterations:,} | Найкращий рахунок: {best_score:,.0f}")

    return best_layout


# ==========================================
# 5. ВІЗУАЛІЗАЦІЯ
# ==========================================
def print_corne(layout):
    print("\n" + "=" * 50)
    print(" БІОМЕХАНІЧНА РОЗКЛАДКА ДЛЯ CORNE 42 (33 літери)")
    print("=" * 50 + "\n")

    L = layout[:15]
    R = layout[15:]

    print(
        f"  {L[0]:^3} {L[1]:^3} {L[2]:^3} {L[3]:^3} {L[4]:^3}      {R[0]:^3} {R[1]:^3} {R[2]:^3} {R[3]:^3} {R[4]:^3} {R[5]:^3}")
    print(
        f"  {L[5]:^3} {L[6]:^3} {L[7]:^3} {L[8]:^3} {L[9]:^3}      {R[6]:^3} {R[7]:^3} {R[8]:^3} {R[9]:^3} {R[10]:^3} {R[11]:^3}")
    print(
        f"  {L[10]:^3} {L[11]:^3} {L[12]:^3} {L[13]:^3} {L[14]:^3}      {R[12]:^3} {R[13]:^3} {R[14]:^3} {R[15]:^3} {R[16]:^3} {R[17]:^3}\n")


if __name__ == "__main__":
    char_counts, bigram_counts = load_corpus(directory="corpus_texts")

    # 1 мільйон ітерацій для пошуку абсолютного ідеалу
    best_layout = optimize_layout(char_counts, bigram_counts, iterations=100000000)

    print_corne(best_layout)