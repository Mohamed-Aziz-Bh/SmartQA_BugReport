import torch
import os
import datetime
import logging
import uvicorn
import base64
import httpx
import pandas as pd
import subprocess
import pickle
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from collections import deque

# --- CONFIGURATION LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartQA-Backend")

app = FastAPI(title="Smart QA Assistant", version="3.0.0")

# --- CONFIGURATION JIRA ---
JIRA_DOMAIN = ""
JIRA_EMAIL = ""
JIRA_API_TOKEN = ""
JIRA_PROJECT_KEY = ""

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- IA SETUP ---
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

# --- LOGIQUE D'APPRENTISSAGE ---

def trigger_auto_learning(failed_step, browser_log, error_details):
    """Ajoute l'erreur inconnue au CSV et relance l'entraînement."""
    try:
        new_data = {
            "selenium_step": [failed_step],
            "user_action": ["Auto-Detected"],
            "browser_log": [browser_log],
            "text": [error_details],
            "user_comment": ["Auto-learning trigger"],
            "label": ["New_Anomalie"],
            "priority": ["HIGH"]
        }
        df_new = pd.DataFrame(new_data)
        
        if os.path.exists(DATASET_PATH):
            df_existing = pd.read_csv(DATASET_PATH)
            df_final = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_final = df_new
            
        df_final.to_csv(DATASET_PATH, index=False)
        logger.info("📝 Dataset mis à jour avec une nouvelle erreur.")

        # Lancement de l'entraînement sans bloquer l'API
        subprocess.Popen(["python", TRAIN_SCRIPT])
        logger.info("🚀 Entraînement du modèle lancé en arrière-plan.")
    except Exception as e:
        logger.error(f"❌ Échec de l'auto-apprentissage: {e}")

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
    category, priority = full_label.split("_") if "_" in full_label else (full_label, "LOW")
    
    return category, priority, confidence

# --- ROUTES API ---

@app.post("/analyze-error")
async def analyze_error(request: Request):
    raw_data = await request.json()
    
    # 1. Extraction et formatage
    failed_step = next((s['text'] for s in raw_data.get("steps", []) if s.get('status') == 'failed'), "N/A")
    browser_log = raw_data.get("browser_log", "No logs")
    error_details = raw_data.get("error_details", "No details")
    input_text = f"[CONTEXT]: {failed_step} | [LOGS]: {browser_log} | [ERROR]: {error_details}"
    
    # 2. Première analyse
    category, priority, confidence = predict_analysis(input_text)
    status_is_failed = (str(raw_data.get("status")).upper() == "FAILED")

    # 3. BOUCLE D'AUTO-APPRENTISSAGE SYNCHRONE
    if status_is_failed and confidence < 0.40:
        logger.info(f"🔍 Inconnu ({int(confidence*100)}%). Lancement du cycle automatique...")
        
        # Cette fonction va maintenant ATTENDRE la fin de l'entraînement
        trigger_auto_learning(failed_step, browser_log, error_details)
        
        # 4. RE-ANALYSE immédiate avec le nouveau modèle
        logger.info("🧠 Nouvelle analyse avec le modèle mis à jour...")
        category, priority, confidence = predict_analysis(input_text)
        suggestion = f"✅ Appris automatiquement | Confiance: {int(confidence*100)}%"
    
    elif not status_is_failed:
        category, priority, suggestion = "Succès", "NONE", "Test réussi."
    else:
        suggestion = f"Confiance IA: {int(confidence*100)}% | Type: {category}"

    # 5. Envoi du rapport final au popup
    final_report = {
        "has_new_data": True,
        "scenario_name": raw_data.get("scenario_name", "Scenario"),
        "status": "FAILED" if status_is_failed else "PASSED",
        "steps": raw_data.get("steps", []),
        "analysis": category,
        "priority": priority,
        "suggestion": suggestion,
        "screenshot": raw_data.get("screenshot"),
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    }

    reports_queue.append(final_report)
    return {"status": "success", "analysis": category}

@app.get("/get-bridge-data")
async def get_bridge_data():
    if reports_queue:
        return reports_queue.popleft()
    return {"has_new_data": False}

# --- JIRA INTEGRATION ---

# --- JIRA INTEGRATION ---

@app.post("/jira/create-session-ticket")
async def create_jira_ticket(request: Request):
    # L'indentation ici doit être de 4 espaces (un seul cran par rapport au "async def")
    data = await request.json()
    test_results = data.get("test_results", [])    
    description_text = "h1. Rapport de Session SmartQA\n\n"
    
    for test in test_results:
        status_icon = "(/)" if test['status'] in ['PASSED', 'SUCCESS', 'passed'] else "(x)"
        description_text += f"h3. {status_icon} Scénario: {test['scenario']}\n"
        
        # Ajout du détail des étapes
        if "steps" in test and test["steps"]:
            description_text += "||Étape||Statut||\n"
            for s in test["steps"]:
                s_icon = "(/)" if s['status'] == 'passed' else "(x)" if s['status'] == 'failed' else "(i)"
                description_text += f"|{s['text']}|{s_icon} {s['status']}|\n"
        
        # Sécurité : on vérifie si ia_analysis existe pour éviter un crash
        ia = test.get('ia_analysis', {})
        description_text += f"\n* *Diagnostic IA:* {ia.get('suggestion', 'N/A')}\n"
        description_text += f"* *Analyse:* {ia.get('details', 'N/A')}\n----\n"

    jira_auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    url = f"https://{JIRA_DOMAIN}/rest/api/2/issue"
    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": f"Rapport QA Session - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "description": description_text,
            "issuetype": {"name": "Bug"}
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, auth=jira_auth)
        if resp.status_code != 201:
            # Si Jira renvoie du HTML (Internal Error), on l'affiche proprement
            logger.error(f"Erreur Jira détaillée : {resp.text}")
            return {"success": False, "error": f"Jira error: {resp.status_code}"}
            
        issue_key = resp.json().get("key")
        try:
         # 1. Formatage propre du JSON
         json_str = json.dumps(data, indent=4, ensure_ascii=False)
         url_attach = f"https://{JIRA_DOMAIN}/rest/api/2/issue/{issue_key}/attachments"
    
         # 2. IMPORTANT : Jira exige ce header spécifique pour les pièces jointes
         headers = {"X-Atlassian-Token": "no-check"}
    
         # 3. Utilisation d'un tuple complet pour le fichier
         # (nom_du_fichier, contenu, type_mime)
         files = {
           "file": ("session_data.json", io.BytesIO(json_str.encode('utf-8')), "application/json")
         }
    
         attach_resp = await client.post(url_attach, headers=headers, files=files, auth=jira_auth)
    
         if attach_resp.status_code == 200:
            logger.info(f"Fichier JSON attaché avec succès à {issue_key}")
         else:
            logger.error(f"Erreur transfert JSON : {attach_resp.status_code} - {attach_resp.text}")
        except Exception as e:
           logger.error(f"Erreur lors de l'envoi du JSON : {e}")
        
        # Upload des screenshots
        for idx, test in enumerate(test_results):
            if test.get("screenshot"):
                await upload_screenshot_to_jira(client, issue_key, test["screenshot"], f"screenshot_{idx}.png", jira_auth)
        
        return {"success": True, "issueKey": issue_key}

async def upload_screenshot_to_jira(client, issue_key, b64_string, filename, auth):
    try:
        # Nettoyage de la chaîne base64
        if "base64," in b64_string:
            b64_string = b64_string.split("base64,")[1]
        
        image_data = base64.b64decode(b64_string)
        url = f"https://{JIRA_DOMAIN}/rest/api/2/issue/{issue_key}/attachments"
        headers = {"X-Atlassian-Token": "no-check"}
        
        files = {"file": (filename, image_data, "image/png")}
        await client.post(url, headers=headers, files=files, auth=auth)
    except Exception as e:
        logger.error(f"Erreur upload screenshot: {e}")
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
