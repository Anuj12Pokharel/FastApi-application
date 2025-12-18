import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or "AIzaSyCFgV6lNsrxNOopUDdeCSYLh_OLO2eh2-E"
genai.configure(api_key=api_key)

print(f"Checking models starting with 'models/gemini'...")

try:
    with open("backend/models.txt", "w") as f:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    f.write(f"{m.name}\n")
                    print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")
