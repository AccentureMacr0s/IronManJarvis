import socket
import json
import speech_recognition as sr
import pyttsx3

def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def listen_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Слушаю...")
        audio = r.listen(source)
    try:
        return r.recognize_google(audio, language="ru-RU").lower()
    except:
        speak("Не понял.")
        return ""

def send_to_node(command_text):
    try:
        data = {"type": "system_command", "text": command_text}
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 5555))
            sock.sendall(json.dumps(data).encode("utf-8"))
    except Exception as e:
        print("Ошибка отправки в Node:", e)

if __name__ == "__main__":
    speak("Дима активен.")
    while True:
        cmd = listen_command()
        if "дима" in cmd:
            clean = cmd.replace("дима", "").strip()
            if "пока" in clean:
                speak("До встречи.")
                break
            speak(f"Команда: {clean}")
            send_to_node(clean)
