import torch
import os
import re
import datetime
import logging
import uvicorn
import base64
import httpx
import pandas as pd
import subprocess
import pickle
import json
import io
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from collections import deque

#Configuration Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartQA-Backend")
app = FastAPI(title="Smart QA Assistant", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
#Configuration Jira/Xray
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
XRAY_CLIENT_ID = os.getenv("XRAY_CLIENT_ID")
XRAY_CLIENT_SECRET = os.getenv("XRAY_CLIENT_SECRET")
XRAY_BASE_URL = os.getenv("XRAY_BASE_URL")

#IA Setup
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_PATH, "D:/smart_qa_model_final")
DATASET_PATH = os.path.join(BASE_PATH, "qa_dataset_v4.csv")
TRAIN_SCRIPT = os.path.join(BASE_PATH, "train_qa_model.py")

tokenizer, model, label_encoder = None, None, None

def load_ai_engine():
    """Charge le modèle, le tokenizer et l'encodeur de labels."""
    global tokenizer, model, label_encoder
    try:
        if os.path.exists(MODEL_PATH) and os.path.exists(os.path.join(MODEL_PATH, "label_encoder.pkl")):
            tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
            model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, ignore_mismatched_sizes=True)
            with open(os.path.join(MODEL_PATH, "label_encoder.pkl"), "rb") as f:
                label_encoder = pickle.load(f)
            logger.info("✅ Moteur IA RoBERTa chargé et prêt.")
        else:
            logger.warning("⚠️ Modèle ou LabelEncoder introuvable. Système en mode passif.")
    except Exception as e:
        logger.error(f"❌ Erreur chargement IA: {e}")

load_ai_engine()
reports_queue = deque(maxlen=50)


def generate_simple_error_comment(error_details):
    """
    Extrait une phrase humaine unique et simple à partir des détails 
    de l'erreur en utilisant des règles de filtrage par Expressions Régulières.
    """
    error_str = str(error_details)
    if "waiting for visibility of" in error_str or "TimeoutException" in error_str:
        match = re.search(r"(?:By\.[a-zA-Z]+|id|css selector):\s*([a-zA-Z0-9_.-]+)", error_str)
        element_name = match.group(1) if match else "l'élément"
        return f"Bouton ou élément '{element_name}' invisible après 10s"

    if "waiting for element to be clickable" in error_str:
        match = re.search(r"(?:By\.[a-zA-Z]+|id|css selector):\s*([a-zA-Z0-9_.-]+)", error_str)
        element_name = match.group(1) if match else "l'élément"
        return f"Élément '{element_name}' présent mais non cliquable (interrompu ou désactivé)"

    if "Unable to locate element" in error_str or "NoSuchElementException" in error_str:
        match = re.search(r"\"selector\":\"([^\"]+)\"", error_str)
        element_name = match.group(1) if match else "demandé"
        return f"Élément '{element_name}' introuvable dans la page"

    if "ElementClickInterceptedException" in error_str or "is not clickable at point" in error_str:
        return "Clic impossible, élément masqué par un autre composant"

    if "404" in error_str or "Not Found" in error_str:
        return "Page ou ressource introuvable (Erreur 404)"
    if "500" in error_str or "Internal Server Error" in error_str:
        return "Erreur interne du serveur distant (Erreur 500)"
    if "403" in error_str or "Forbidden" in error_str:
        return "Accès refusé par le serveur (Erreur 403)"

    if "connection reset" in error_str.lower() or "connection refused" in error_str.lower():
        return "Connexion réseau coupée brutalement par l'hôte"

    if "UnexpectedAlertPresentException" in error_str:
        return "Une alerte JavaScript inattendue bloque l'action"

    first_line = error_str.split('\n')[0]
    match_exception = re.match(r"^([a-zA-Z]+Exception):", first_line)
    if match_exception:
        return f"Échec critique causé par {match_exception.group(1)}"
        
    return "Anomalie ou action en timeout sur l'application"

def get_error_short_label(error_text):
    """
    Extrait automatiquement le nom de l'exception Java et le formate proprement.
    Exemple: 'org.openqa.selenium.NoSuchElementException: ...' -> 'No Such Element'
    """
    if not error_text or error_text == "No details":
        return "Unknown Tech"
    match = re.search(r'([a-zA-Z0-9]+(?:Exception|Error))', error_text)
    
    if match:
        exception_name = match.group(1)
        clean_name = exception_name.replace("Exception", "").replace("Error", "")
        formatted_label = re.sub(r'([A-Z])', r' \1', clean_name).strip()
        return formatted_label
    words = error_text.split()[:3]
    return " ".join(words).strip() if words else "Technical Issue"

def clean_error_for_dataset(error_text):
    first_line = error_text.split('\n')[0]
    clean_text = re.sub(r'\(tried for \d+ second\(s\).*?\)', '', first_line).strip()
    return clean_text    

#Logique d'apprentissage
def trigger_auto_learning(failed_step, browser_log, error_details):
    """Vérifie l'existence de l'erreur avant de l'ajouter et de réentraîner."""
    try:
        corrected_error_details = clean_error_for_dataset(error_details)
        user_comment_phrase = generate_simple_error_comment(corrected_error_details)
        short_label = get_error_short_label(corrected_error_details)
        tech_label = short_label.replace(" ", "_")
        new_row = {
            "selenium_step": str(failed_step),
            "user_action": "Auto-Detected",
            "browser_log": str(browser_log),
            "text": str(corrected_error_details),
            "user_comment": str(user_comment_phrase),
            "label": f"New_Anomalie_{tech_label}",
            "priority": "HIGH"
        }

        if os.path.exists(DATASET_PATH):
            df_existing = pd.read_csv(DATASET_PATH)
            is_duplicate = df_existing[
                (df_existing['text'] == new_row['text']) & 
                (df_existing['browser_log'] == new_row['browser_log'])
            ].any().any()

            if is_duplicate:
                logger.info("ℹ️ Erreur déjà présente dans le dataset. Pas d'ajout nécessaire.")
                return False
            
            df_final = pd.concat([df_existing, pd.DataFrame([new_row])], ignore_index=True)
        else:
            df_final = pd.DataFrame([new_row])
            
        df_final.to_csv(DATASET_PATH, index=False)
        logger.info("📝 Dataset mis à jour : Nouvelle erreur unique ajoutée.")
        #model = None 
        #tokenizer = None
        #import gc
        #gc.collect()
        #subprocess.Popen(["python", TRAIN_SCRIPT])
        #logger.info("🚀 Entraînement du modèle lancé en arrière-plan.")
        return True

    except Exception as e:
        logger.error(f"❌ Échec de l'auto-apprentissage: {e}")
        return False

def predict_analysis(text: str):
    if not model or not tokenizer:
        return "Analyse Indisponible", "LOW", 0.0
    
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        outputs = model(**inputs)
    
    probs = torch.softmax(outputs.logits, dim=-1)
    label_id = torch.argmax(probs).item()
    confidence = probs[0][label_id].item()
    
    full_label = model.config.id2label.get(label_id, "Inconnu_LOW")

    if "_" in full_label:
        parts = full_label.rsplit("_", 1)
        category = parts[0]
        priority = parts[1]
    else:
        category = full_label
        priority = "LOW"
    
    return category, priority, confidence

#API
@app.post("/analyze-error")
async def analyze_error(request: Request):
    raw_data = await request.json()
    steps = raw_data.get("steps", [])
    failed_step = next((s['text'] for s in steps if s.get('status') == 'failed'), "N/A")
    browser_log = raw_data.get("browser_log", "No logs")
    error_details = raw_data.get("error_details", "No details")
    user_comment = generate_simple_error_comment(error_details)
    error_clean = clean_error_for_dataset(error_details)
    input_text = f"[CONTEXT]: {failed_step} | [ERROR]: {error_clean}"
    category, priority, confidence = predict_analysis(input_text)
    status_is_failed = (str(raw_data.get("status")).upper() == "FAILED")
    suggestion = ""
    if status_is_failed:
        if confidence < 0.40:
            logger.info(f"🔍 Confiance faible ({int(confidence*100)}%). Automatisation du diagnostic...")
            corrected_error_details = clean_error_for_dataset(error_details)
            short_type = get_error_short_label(corrected_error_details)
            trigger_auto_learning(failed_step, browser_log, corrected_error_details)
            category = f"New_Anomalie: {short_type}"
            priority = "HIGH"
            suggestion = f"✅ Erreur apprise automatiquement | {user_comment}"
        else:
            suggestion = f"Analyse confirmée à {int(confidence*100)}% par l'IA"
            
    elif not status_is_failed:
        category, priority, suggestion = "Succès", "NONE", "Test réussi avec succès."

    final_report = {
        "has_new_data": True,
        "scenario_name": raw_data.get("scenario_name", "Scenario"),
        "status": "FAILED" if status_is_failed else "PASSED",
        "steps": steps,
        "analysis": category,
        "priority": priority,
        "suggestion": suggestion,
        "screenshot": raw_data.get("screenshot"),
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    }

    reports_queue.append(final_report)
    logger.info(f"📊 Rapport généré : {category} ({priority})")
    
    return {"status": "success", "analysis": category}

@app.get("/get-bridge-data")
async def get_bridge_data():
    if reports_queue:
        return reports_queue.popleft()
    return {"has_new_data": False}



#xray / jira
async def get_xray_token():
    url = f"{XRAY_BASE_URL}/authenticate"
    payload = {
        "client_id": XRAY_CLIENT_ID,
        "client_secret": XRAY_CLIENT_SECRET
    }
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise Exception(resp.text)
        return resp.text.replace('"', '')

async def search_test(client, scenario):
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    safe_scenario = scenario.replace('"', '\\"')
    jql = f'project = {JIRA_PROJECT_KEY} AND issuetype = Test AND summary ~ "{safe_scenario}"'
    resp = await client.get(
        url,
        params={"jql": jql, "maxResults": 1},
        auth=(JIRA_EMAIL, JIRA_API_TOKEN)
    )
    if resp.status_code != 200:
        print(f"[RECHERCHE] Erreur API Jira ({resp.status_code}): {resp.text}")
        return None
    data = resp.json()
    issues = data.get("issues", [])
    if issues and isinstance(issues[0], dict) and "key" in issues[0]:
        return issues[0]["key"]
    return None

async def create_test_with_steps(client, token, test):
    url = "https://eu.xray.cloud.getxray.app/api/v2/graphql"
    scenario = test.get("scenario", "Auto Test")
    steps = test.get("steps", [])
    gherkin = "\n".join([s.get("text", "") for s in steps])
    query = """
    mutation CreateTest($summary: String!, $gherkin: String!, $projectKey: String!) {
      createTest(
        testType: { name: "Cucumber" }
        jira: {
          fields: {
            project: { key: $projectKey }
            summary: $summary
          }
        }
        gherkin: $gherkin
      ) {
        test {
          issueId
        }
      }
    }
    """
    payload = {
        "query": query,
        "variables": {
            "summary": scenario,
            "gherkin": gherkin,
            "projectKey": JIRA_PROJECT_KEY
        }
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        resp = await client.post(url, json=payload, headers=headers)
        print("STATUS:", resp.status_code)
        if resp.status_code != 200:
            raise Exception(resp.text)
        data = resp.json()
        if "errors" in data:
            raise Exception(data["errors"])
        return data["data"]["createTest"]["test"].get("issueId")        
    except httpx.ReadTimeout:
        print(f"[TIMEOUT] L'API Xray a mis trop de temps à répondre pour : {scenario}")
        raise Exception("Xray API Read Timeout")

async def execute_tests(token, tests):
    url = "https://eu.xray.cloud.getxray.app/api/v2/import/execution"
    cleaned_tests_payload = []
    for t in tests:
        test_key = t.get("testKey")
        if not test_key:
            continue   
        status_raw = t.get("status", "").lower()
        status_final = "PASSED" if status_raw in ["passed", "success"] else "FAILED"
        test_entry = {
            "testKey": str(test_key),
            "status": status_final,
            "comment": str(t.get("analysis", ""))
        }
        if "defectKey" in t:
            test_entry["defects"] = [t["defectKey"]]
        cleaned_tests_payload.append(test_entry)
    payload = {
        "info": {
            "summary": "SmartQA Execution",
            "description": "Execution automatique générée par SmartQA Assistant"
        },
        "tests": cleaned_tests_payload
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        return resp.json()

async def create_bug(client, test):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    steps = "\n".join([
        f"- {s.get('text')} ({s.get('status')})"
        for s in test.get("steps", [])
    ])
    analysis_text = f"{test.get('analysis','')}\nSuggestion: {test.get('suggestion','')}"
    full_description_text = f"Scenario:\n{test.get('scenario')}\n\nSteps:\n{steps}\n\nAI Analysis:\n{analysis_text}"
    adf_description = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": full_description_text
                    }
                ]
            }
        ]
    }

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": f"[BUG] {test.get('scenario')}",
            "description": adf_description,
            "issuetype": {"name": "Bug"},
            "labels": ["smartqa", "auto-bug"]
        }
    }

    resp = await client.post(
        url,
        json=payload,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN)
    )
    if resp.status_code != 201:
        print(f"❌ Erreur Jira lors de la création du bug ({resp.status_code}) : {resp.text}")
        raise Exception(f"Jira API Error 400: {resp.text}")
    return resp.json()["key"]

async def upload_screenshot_to_bug(client, bug_key, image_data, filename="screenshot.png"):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{bug_key}/attachments"
    if isinstance(image_data, str):
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]        
        image_data = image_data.strip()        
        try:
            binary_data = base64.b64decode(image_data)
        except Exception as e:
            print(f"[ERREUR] Échec du décodage Base64 du screenshot : {e}")
            return None
    else:
        binary_data = image_data
    files = {
        "file": (filename, binary_data, "image/png")
    }

    bug_headers = {
        "X-Atlassian-Token": "no-check"
    }

    resp = await client.post(
        url,
        files=files,
        headers=bug_headers,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN)
    )
    
    return resp

@app.post("/xray/execute")
async def send_to_xray(request: Request):

    data = await request.json()
    test_results = data.get("test_results", [])

    token = await get_xray_token()

    enriched = []
    bugs = []
    new_tests_created = False

    async with httpx.AsyncClient(timeout=60) as client:
        for t in test_results:
            scenario = t.get("scenario")
            test_key = await search_test(client, scenario)

            if not test_key:
                new_tests_created = True
                issue_id = await create_test_with_steps(client, token, t)
                
                try:
                    jira_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_id}"
                    jira_resp = await client.get(jira_url, auth=(JIRA_EMAIL, JIRA_API_TOKEN))
                    if jira_resp.status_code == 200:
                        test_key = jira_resp.json().get("key")
                    else:
                        test_key = issue_id 
                except Exception as e:
                    print(f"[ERREUR] Clé introuvable pour l'ID {issue_id}: {e}")
                    test_key = issue_id

            enriched.append({
                **t,
                "testKey": test_key
            })
        if new_tests_created:
            print("[INFO] Pause de 4 secondes pour l'indexation Xray Cloud...")
            await asyncio.sleep(4.0)
        for t in enriched:
            status = t.get("status", "").lower()
            if status not in ["passed", "success"]:
                bug_key = await create_bug(client, t)
                screenshot = t.get("screenshot")
                if screenshot:
                    await upload_screenshot_to_bug(client, bug_key, screenshot)
                t["defectKey"] = bug_key
                bugs.append({
                    "test": t["testKey"],
                    "bug": bug_key
                })

        execution = await execute_tests(token, enriched)

        return {
            "success": True,
            "execution": execution,
            "tests": enriched,
            "bugs": bugs
        }
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)