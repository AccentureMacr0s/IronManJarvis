import os
import sys
from modules.voice import speak

def check_for_self_update(code):
    if "# SELF-MODIFY" in code:
        speak("Обновляю себя...")
        try:
            with open(__file__, "r") as f:
                original = f.read()

            new_code = code.split("# SELF-MODIFY")[-1].strip()
            with open(__file__, "w") as f:
                f.write(new_code)

            speak("Перезапуск...")
            os.execv(sys.executable, ['python3'] + sys.argv)
        except Exception as e:
            speak(f"Не удалось обновиться: {str(e)}")
