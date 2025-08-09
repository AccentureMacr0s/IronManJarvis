import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_openai(prompt):
    messages = [
        {"role": "system", "content": "Ты голосовой ассистент JARVIS. Отвечай кратко, точно, с уважением."},
        {"role": "user", "content": prompt}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )
    return response['choices'][0]['message']['content']
