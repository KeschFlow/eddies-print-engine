# gpt_module.py

import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_vocab(topic: str, level: str = "A1") -> str:
    prompt = f"""
    Erstelle 10 einfache Fachvokabeln zum Thema '{topic}'.
    Sprachniveau: {level}
    Format:
    Wort;Übersetzung
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content


def generate_mission(theme: str, difficulty: int, audience: str) -> str:
    prompt = f"""
    Erstelle eine Quest-Mission.
    Thema: {theme}
    Schwierigkeit: {difficulty} (1-5)
    Zielgruppe: {audience}

    Format:
    Titel:
    Bewegung:
    Denken:
    Proof:
    XP:
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    return response.choices[0].message.content
