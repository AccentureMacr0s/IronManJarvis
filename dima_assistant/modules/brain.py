import openai
import json
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

with open("config.json") as f:
    config = json.load(f)

def ask_openai(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"Ты помощник по имени {config['name']}. {config['current_role']}"},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']
