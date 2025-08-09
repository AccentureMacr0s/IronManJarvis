from modules.voice import listen_command, speak
from modules.brain import ask_openai
from modules.executor import execute_generated_code
from modules.updater import check_for_self_update
import json

with open("config.json") as f:
    config = json.load(f)

def main():
    speak(f"Привет, я {config['name']}. {config['personality']}")
    while True:
        command = listen_command()
        if config['name'].lower() in command:
            if "пока" in command:
                speak("До встречи!")
                break
            elif "сменим профессию" in command:
                new_role = command.split("профессию")[-1].strip()
                config['current_role'] = new_role
                with open("config.json", "w") as f:
                    json.dump(config, f)
                speak(f"Теперь я {new_role}")
            else:
                prompt = command.replace(config['name'].lower(), "").strip()
                full_prompt = f"Ты {config['current_role']}. {prompt}"
                code = ask_openai(full_prompt)
                execute_generated_code(code)
                check_for_self_update(code)

if __name__ == "__main__":
    main()
