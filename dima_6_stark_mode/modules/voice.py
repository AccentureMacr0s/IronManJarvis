import speech_recognition as sr
import pyttsx3

engine = pyttsx3.init()

def speak(text):
    print(f"[Дима]: {text}")
    engine.say(text)
    engine.runAndWait()

def listen_command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Слушаю...")
        audio = recognizer.listen(source)
    try:
        command = recognizer.recognize_google(audio, language="ru-RU")
        print(f"🗣️ Ты сказал: {command}")
        return command.lower()
    except Exception:
        speak("Ошибка распознавания.")
        return ""
