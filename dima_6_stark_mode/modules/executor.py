import os
from modules.voice import speak

def handle_command(command):
    # Упрощённый список действий
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
