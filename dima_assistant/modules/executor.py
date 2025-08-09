import os
import subprocess
from modules.voice import speak
import json

with open("config.json") as f:
    config = json.load(f)

def execute_generated_code(code):
    if "sudo" in code and not config.get("allow_sudo", False):
        speak("Эта команда требует sudo, но это запрещено в настройках.")
        return

    if config.get("execution_mode", "confirm") == "confirm":
        if "sudo" in code:
            speak("Обнаружен sudo. Подтвердите выполнение.")
        else:
            speak("Подтвердите выполнение.")
        confirmation = input("Выполнить? (да/нет): ").lower()
        if "да" not in confirmation:
            speak("Отменено.")
            return

    try:
        exec(code, globals())
        speak("Готово.")
    except Exception as e:
        speak(f"Ошибка: {str(e)}")
