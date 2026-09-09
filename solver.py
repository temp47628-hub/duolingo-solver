import ollama
import pyautogui
import pyperclip
import time
import json
import re
import random
import math

SCREENSHOT = r"C:\Duolingo-Solver\duolingo.png"

print("Starting in 3 seconds...")
time.sleep(3)

# Take screenshot
screenshot = pyautogui.screenshot()
screenshot.save(SCREENSHOT)

width, height = screenshot.size

print(f"Screenshot: {width}x{height}")
print("Sending screenshot to Qwen...")

prompt = f"""
You are an AI that solves Duolingo exercises.

Analyze the screenshot carefully.

Determine what type of exercise this is.

Possible types:
- "missing_word" = there is a blank/text input that needs typing
- "word_bank" = answer choices are buttons that need clicking
- "other" = something else

For a missing_word exercise:
- Find the exact answer that belongs in the blank.
- Find the CENTER coordinates of the blank/input field.

For a word_bank exercise:
- Determine the correct words and their order.
- Find the CENTER coordinates of every required answer button.

The screenshot resolution is {width}x{height}.

Return ONLY valid JSON.
Do NOT use markdown.
Do NOT explain anything.

For missing_word use:

{{
    "type": "missing_word",
    "answer": "answer",
    "input": {{"x": 0, "y": 0}}
}}

For word_bank use:

{{
    "type": "word_bank",
    "answer": ["word1", "word2"],
    "buttons": [
        {{"text": "word1", "x": 0, "y": 0}},
        {{"text": "word2", "x": 0, "y": 0}}
    ]
}}
"""

response = ollama.chat(
    model="qwen3-vl:8b",
    messages=[
        {
            "role": "user",
            "content": prompt,
            "images": [SCREENSHOT]
        }
    ]
)

raw = response["message"]["content"].strip()

print("\nQwen response:")
print(raw)

# Remove accidental markdown fences
raw = re.sub(r"```json|```", "", raw).strip()

# Pull out the first {...} block in case there's stray text around it
match = re.search(r"\{.*\}", raw, re.DOTALL)
if match:
    raw = match.group(0)

try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print("\nERROR: Qwen did not return valid JSON.")
    exit()

exercise_type = data.get("type")


# =========================
# HUMAN-LIKE MOUSE MOVEMENT
# =========================

def human_move(x, y, duration=None):
    """Move the mouse to (x, y) along a slightly curved path with
    variable speed, instead of teleporting."""
    start_x, start_y = pyautogui.position()

    distance = math.hypot(x - start_x, y - start_y)
    if duration is None:
        duration = min(0.9, max(0.25, distance / 1800))

    steps = max(15, int(distance / 12))

    curve_strength = random.uniform(0.05, 0.18) * distance
    angle = math.atan2(y - start_y, x - start_x) + math.pi / 2
    ctrl_x = (start_x + x) / 2 + curve_strength * math.cos(angle)
    ctrl_y = (start_y + y) / 2 + curve_strength * math.sin(angle)

    for i in range(1, steps + 1):
        t = i / steps
        ix = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * x
        iy = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * y

        ix += random.uniform(-1, 1)
        iy += random.uniform(-1, 1)

        pyautogui.moveTo(ix, iy, duration=0)
        time.sleep(duration / steps * random.uniform(0.7, 1.3))

    pyautogui.moveTo(x, y, duration=0)


def human_click(x, y):
    human_move(x, y)
    time.sleep(random.uniform(0.05, 0.15))
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.04, 0.11))
    pyautogui.mouseUp()


def human_type(text, wpm=140):
    """Type text one character at a time at roughly the given WPM,
    with natural variance and occasional tiny pauses, instead of
    pasting it all at once."""
    # Standard typing-speed convention: 1 "word" = 5 characters
    chars_per_sec = (wpm * 5) / 60
    base_delay = 1 / chars_per_sec

    for ch in text:
        pyautogui.write(ch)

        # per-character variance so it's not perfectly metronomic
        delay = base_delay * random.uniform(0.55, 1.6)

        # occasional longer "thinking" pause, more likely after spaces/punctuation
        if ch in " ,.!?" and random.random() < 0.15:
            delay += random.uniform(0.08, 0.25)
        elif random.random() < 0.04:
            delay += random.uniform(0.1, 0.3)

        time.sleep(delay)


def human_drag(start_x, start_y, end_x, end_y):
    """Real drag: mouse down, move along a curved path, mouse up.
    Use instead of human_click when an exercise needs an actual
    drag-and-drop rather than a click."""
    human_move(start_x, start_y)
    time.sleep(random.uniform(0.05, 0.12))
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.05, 0.1))

    steps = max(15, int(math.hypot(end_x - start_x, end_y - start_y) / 12))
    for i in range(1, steps + 1):
        t = i / steps
        ix = start_x + (end_x - start_x) * t + random.uniform(-1, 1)
        iy = start_y + (end_y - start_y) * t + random.uniform(-1, 1)
        pyautogui.moveTo(ix, iy, duration=0)
        time.sleep(random.uniform(0.008, 0.02))

    pyautogui.moveTo(end_x, end_y, duration=0)
    time.sleep(random.uniform(0.05, 0.12))
    pyautogui.mouseUp()


# =========================
# MISSING WORD
# =========================

if exercise_type == "missing_word":

    answer = data["answer"]
    input_pos = data["input"]

    print("\nExercise: Missing word")
    print("Answer:", answer)

    # Click the blank
    human_click(input_pos["x"], input_pos["y"])

    time.sleep(0.3)

    # Type answer naturally, ~140 wpm with human variance
    human_type(answer, wpm=140)

    print("Answer entered! (Check not pressed — press it yourself)")


# =========================
# WORD BANK
# =========================

elif exercise_type == "word_bank":

    answer = data["answer"]
    buttons = data["buttons"]

    print("\nExercise: Word bank")
    print("Answer:", " → ".join(answer))

    # Track available positions per word so duplicates don't collide
    positions = {}
    for button in buttons:
        key = button["text"].lower()
        positions.setdefault(key, []).append((button["x"], button["y"]))

    for word in answer:
        key = word.lower()

        if key not in positions or not positions[key]:
            print("Couldn't find:", word)
            continue

        x, y = positions[key].pop(0)

        print(f"Clicking {word} at ({x}, {y})")
        human_click(x, y)
        time.sleep(random.uniform(0.2, 0.4))

    print("Words entered! (Check not pressed — press it yourself)")


# =========================
# UNKNOWN
# =========================

else:

    print("\nI don't know how to solve this exercise type yet.")

    print("Detected type:", exercise_type)


input("\nPress ENTER to close...")
