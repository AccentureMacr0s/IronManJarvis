from modules.voice import listen_command, speak
from modules.executor import handle_command
import json

with open("config.json") as f:
    config = json.load(f)

def main():
    speak(f"{config['name']} в режиме Stark с поддержкой общения.")
    while True:
        command = listen_command()
        if config['name'].lower() in command:
            if "пока" in command:
                speak("Отключаюсь.")
                break
            else:
                instruction = command.replace(config['name'].lower(), "").strip()
                handle_command(instruction)

if __name__ == "__main__":
    main()
