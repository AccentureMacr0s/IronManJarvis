import os
import json
from modules.voice import speak
from modules.brain import ask_openai

with open("config.json") as f:
    config = json.load(f)

def handle_command(command):
    if "режим общения" in command:
        config["chat_mode"] = True
        with open("config.json", "w") as f:
            json.dump(config, f)
        speak("Режим общения активирован.")
        return

    if "отключи общение" in command:
        config["chat_mode"] = False
        with open("config.json", "w") as f:
            json.dump(config, f)
        speak("Режим общения отключён.")
        return

    if config.get("chat_mode", False):
        response = ask_openai(command)
        speak(response)
        return

    if "открой проект" in command:
        folder = command.split("проект")[-1].strip()
        speak(f"Открываю папку {folder}")
        os.system(f"code {folder}")
    elif "создай скрипт архив" in command:
        script = "#!/bin/bash\ntar -czf archive.tar.gz ./папка"
        with open("archive.sh", "w") as f:
            f.write(script)
        speak("Скрипт сохранён. Открываю.")
        os.system("code archive.sh")
    elif "открой файл" in command:
        filename = command.split("файл")[-1].strip()
        speak(f"Открываю {filename}")
        os.system(f"code {filename}")
    else:
        speak("Команда не распознана.")
