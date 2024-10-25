from datetime import datetime
from fhirpathpy import evaluate
from dotenv import load_dotenv
import os
from openai import OpenAI
import requests
import json
from ollama import Client
from bs4 import BeautifulSoup
from groq import Groq


load_dotenv()


SERVER_URL = os.getenv("SERVER_URL")
MODEL_URL = os.getenv("MODEL_URL")
client = Client(host=MODEL_URL)

if MODEL_URL is None:
    client = OpenAI(
        # This is the default and can be omitted
        api_key=os.getenv("OPENAI_KEY"),
    )
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )

LANGUAGE_MAP = {
    "es": "Spanish",
    "en": "English",
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "tr": "Turkish",
    "ar": "Arabic",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "vi": "Vietnamese",
    "th": "Thai",
    "el": "Greek",
    "cs": "Czech",
    "hu": "Hungarian",
    "ro": "Romanian",
    "sv": "Swedish",
    "fi": "Finnish",
    "da": "Danish",
    "no": "Norwegian",
    "is": "Icelandic",
    "et": "Estonian",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "mt": "Maltese",
    "hr": "Croatian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "bg": "Bulgarian",
    "cy": "Welsh",
    "ga": "Irish",
    "gd": "Gaelic",
    "eu": "Basque",
    "ca": "Catalan",
    "gl": "Galician",
}


def process_bundle(bundle):
    # print(bundle)
    mp = evaluate(
        bundle,
        "Bundle.entry.where(resource.resourceType=='MedicinalProductDefinition')",
        [],
    )[0]["resource"]
    #  print(mp)
    drug_name = mp["name"][0]["productName"]
    language = bundle["language"]
    # print(language)
    comp = bundle["entry"][0]["resource"]
    epi_full_text = []
    for sec in comp["section"]:
        if sec.get("section"):
            for subsec in sec["section"]:
                #  print(subsec["text"]["div"])
                epi_full_text.append({subsec["title"]: subsec["text"]["div"]})
    # print(sec["text"])

    return language, epi_full_text, drug_name


def process_ips(ips):
    # print(ips)
    pat = evaluate(ips, "Bundle.entry.where(resource.resourceType=='Patient')", [])[0][
        "resource"
    ]

    gender = pat["gender"]
    bd = pat["birthDate"]

    # Convert the string to a datetime object
    birth_date = datetime.strptime(bd, "%Y-%m-%d")

    # Get the current date
    current_date = datetime.now()

    # Calculate the age
    age = (
        current_date.year
        - birth_date.year
        - ((current_date.month, current_date.day) < (birth_date.month, birth_date.day))
    )
    conditions = evaluate(
        ips, "Bundle.entry.where(resource.resourceType=='Condition')", []
    )
    diagnostics = []
    # print(conditions)
    for cond in conditions:
        diagnostics.append(cond["resource"]["code"]["text"])

    medications = evaluate(
        ips, "Bundle.entry.where(resource.resourceType=='Medication')", []
    )
    meds = []
    for med in medications:
        meds.append(med["resource"]["code"]["coding"][0]["display"])

    return gender, age, diagnostics, meds


def transform_fhir_epi(epi):
    # print(epi)
    new_epi = ""
    idx = 0

    for ep in epi:
        # print("eeeeeeee", ep)
        idx += 1
        for k, v in ep.items():
            if idx < 8:
                #  print(idx, "----", k, v)
                soup = BeautifulSoup(v, "html.parser")
                cleaned_html = ""
                # Remove all text nodes
                for element in soup.find_all(text=True):
                    #  print(element)
                    cleaned_html += element.extract() + " "

                new_epi += "\n" + k + "\n\n" + cleaned_html
    print("LENGTH", len(new_epi))
    print("LENGTH", len(new_epi.split()))
    return new_epi


def medicationchat(
    language,
    drug_name,
    gender,
    age,
    diagnostics,
    medications,
    question,
    epi,
    model="llama3",
):
    # print(model)
    epi_text = transform_fhir_epi(epi)
    # epi_text = [k + v for k, v in epi[0].items()]

    # print(epi_text)
    # model = "gpt-4"
    # print(drug_name)
    lang = LANGUAGE_MAP[language]
    prompt = (
        "Answer the question based on the context below. If you don't know the answer based on the context provided below, just respond with 'I don't know' instead of making up an answer. Return just the answer to the question, don't add anything else. Don't start your response with the word 'Answer:'. Make sure your response is in markdown format\n\n"
        + "You can only speak and answer in "
        + lang
        + " language and this is totally mandatory. Otherwise I will not understand."
        + "Context:\n"
        + epi_text
        + "\n\nQuestion:\n\n"
        + question
        + "\n\nAnswer:\n\n"
    )
    systemMessage = (
        """
        You must follow this indications extremety strictly:\n
        1. You must answer in """
        + lang
        + """ \n
        2. You must take into account the patient information. \n
        3. You can only speak in """
        + lang
        + """ only and this is mandatory \n
        4. You MUST be impersonal and refer to the patient as a person, but NEVER for its name.\n
        5. You must be direct and MUST NOT GREET the patient.\n
        6. Translate any other language to the """
        + lang
        + """ language whenever possible.
        """
    )
    # print(prompt)
    if "llama3" == model:
        #   print("prompt is:" + prompt)

        prompt_message = prompt

        result = client.chat(
            model="llama3",
            messages=[
                {"content": systemMessage, "role": "system"},
                {"content": prompt_message, "role": "user"},
            ],
            stream=False,
        )

        response = result["message"]["content"]
        print("Response:", response)
    if "gorq-llama3-70" in model:
        prompt_message = prompt

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": systemMessage},
                {"role": "user", "content": prompt_message},
            ],
            model="llama3-70b-8192",
            temperature=0.05,
        )

        response = chat_completion.choices[0].message.content
        print(response)
    return {
        "response": response,
        "prompt": prompt,
        "datetime": datetime.now().isoformat(),
        "model": model,
        "question": question,
    }
