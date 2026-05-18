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
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from collections import deque

# --- CONFIGURATION LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartQA-Backend")

app = FastAPI(title="Smart QA Assistant", version="3.0.0")

# --- CONFIGURATION JIRA ---
JIRA_BASE_URL = "https://azizbelhadjyoussef37.atlassian.net"
JIRA_EMAIL = "azizbelhadjyoussef37@gmail.com"
JIRA_API_TOKEN = "ATATT3xFfGF0I_tFpMFmkLL6ygnE4F5cl8GJV1res7nOuN92lI-UCXcLo3_ar6LsV9n1wCC-PvPYgwadAN7SeVxpoVwIwzp_EUGpZYkK3zgjZFW6nyNB4NujVhANxfEJYewVSr_u-JYT80eAooe-4MlvCGsxGd2_jRBwjWqPtjhqN2RZF4vpF60=F191FECE"
JIRA_PROJECT_KEY = "KAN"

#-- Configuration Xray ---
XRAY_CLIENT_ID = "4383FBDDE311410EA17913A9BD3020B1"
XRAY_CLIENT_SECRET = "49536f3278a1daa5b92d0a6cb093ac89bf47c7cb90b82f014e1fbe967b130ed8"
XRAY_BASE_URL = "https://eu.xray.cloud.getxray.app/api/v2"

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

def get_error_short_label(error_text):
    """
    Extrait automatiquement le nom de l'exception Java et le formate proprement.
    Exemple: 'org.openqa.selenium.NoSuchElementException: ...' -> 'No Such Element'
    """
    if not error_text or error_text == "No details":
        return "Unknown Tech"

    # 1. On cherche un mot qui finit par Exception ou Error (ex: TimeoutException)
    # On capture uniquement le nom de la classe, sans le package (le dernier mot avant les ':')
    match = re.search(r'([a-zA-Z0-9]+(?:Exception|Error))', error_text)
    
    if match:
        exception_name = match.group(1)
        
        # 2. On retire le suffixe "Exception" ou "Error" pour alléger le label
        clean_name = exception_name.replace("Exception", "").replace("Error", "")
        
        # 3. On ajoute des espaces entre les majuscules (ex: NoSuchElement -> No Such Element)
        # On utilise une expression régulière pour trouver les majuscules
        formatted_label = re.sub(r'([A-Z])', r' \1', clean_name).strip()
        
        return formatted_label
    
    # Si on ne trouve pas de classe d'exception, on prend les 3 premiers mots du message
    words = error_text.split()[:3]
    return " ".join(words).strip() if words else "Technical Issue"

def clean_error_for_dataset(error_text):
    # 1. On ne garde que la PREMIÈRE ligne (qui contient la vraie erreur)
    # On ignore les lignes "Build info:", "System info:", "Capabilities..."
    first_line = error_text.split('\n')[0]
    
    # 2. On supprime les variables de temps (qui changent à chaque test) pour uniformiser
    # Ex: (tried for 10 second(s) with 500 milliseconds interval) -> supprimé
    clean_text = re.sub(r'\(tried for \d+ second\(s\).*?\)', '', first_line).strip()
    
    return clean_text    

# --- LOGIQUE D'APPRENTISSAGE ---
def trigger_auto_learning(failed_step, browser_log, error_details):
    """Vérifie l'existence de l'erreur avant de l'ajouter et de réentraîner."""
    try:
        corrected_error_details = clean_error_for_dataset(error_details)
        # APPEL DE LA FONCTION AUTOMATISÉE
        short_label = get_error_short_label(corrected_error_details)
        # On remplace les espaces par des underscores pour le label technique
        tech_label = short_label.replace(" ", "_")
        # 1. Préparation de la nouvelle entrée
        new_row = {
            "selenium_step": str(failed_step),
            "user_action": "Auto-Detected",
            "browser_log": str(browser_log),
            "text": str(corrected_error_details),
            "user_comment": "Auto-learning trigger",
            "label": f"New_Anomalie_{tech_label}",
            "priority": "HIGH"
        }

        if os.path.exists(DATASET_PATH):
            df_existing = pd.read_csv(DATASET_PATH)
            
            # --- LOGIQUE ANTI-DUPLICATA ---
            # On vérifie si une ligne avec le même message d'erreur (text) 
            # et le même log existe déjà
            is_duplicate = df_existing[
                (df_existing['text'] == new_row['text']) & 
                (df_existing['browser_log'] == new_row['browser_log'])
            ].any().any()

            if is_duplicate:
                logger.info("ℹ️ Erreur déjà présente dans le dataset. Pas d'ajout nécessaire.")
                return False # On sort sans rien faire
            
            df_final = pd.concat([df_existing, pd.DataFrame([new_row])], ignore_index=True)
        else:
            df_final = pd.DataFrame([new_row])
            
        # 2. Sauvegarde
        df_final.to_csv(DATASET_PATH, index=False)
        logger.info("📝 Dataset mis à jour : Nouvelle erreur unique ajoutée.")

        # 3. Lancement de l'entraînement
        # Note: subprocess.Popen est non-bloquant. 
        # Ton code actuel attend une ré-analyse immédiate, 
        # mais l'entraînement prend du temps (plusieurs minutes).
        model = None 
        tokenizer = None
        import gc
        gc.collect()
        
        subprocess.Popen(["python", TRAIN_SCRIPT])
        logger.info("🚀 Entraînement du modèle lancé en arrière-plan.")
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

    # 1. Extraction Catégorie et Priorité
    if "_" in full_label:
        parts = full_label.rsplit("_", 1)
        category = parts[0]
        priority = parts[1]
    else:
        category = full_label
        priority = "LOW"

    # 2. NETTOYAGE : Si c'est un label auto-appris, on le rend beau pour le popup
    # "New_Anomalie_Stale_Element" -> "Stale Element"
    category = category.replace("New_Anomalie_", "").replace("_", " ")
    
    return category, priority, confidence

# --- ROUTES API ---

@app.post("/analyze-error")
async def analyze_error(request: Request):
    raw_data = await request.json()
    
    # 1. Extraction et formatage
    steps = raw_data.get("steps", [])
    failed_step = next((s['text'] for s in steps if s.get('status') == 'failed'), "N/A")
    browser_log = raw_data.get("browser_log", "No logs")
    error_details = raw_data.get("error_details", "No details")
    
    error_clean = clean_error_for_dataset(error_details)
    input_text = f"[CONTEXT]: {failed_step} | [ERROR]: {error_clean}"
    
    # 2. Première analyse par l'IA
    category, priority, confidence = predict_analysis(input_text)
    status_is_failed = (str(raw_data.get("status")).upper() == "FAILED")
    
    suggestion = ""

    # 3. LOGIQUE D'AUTO-APPRENTISSAGE ET AFFICHAGE DYNAMIQUE
    if status_is_failed:
        if confidence < 0.40:
            logger.info(f"🔍 Confiance faible ({int(confidence*100)}%). Automatisation du diagnostic...")
            
            # On génère le label propre immédiatement (Option 1)
            corrected_error_details = clean_error_for_dataset(error_details)
            short_type = get_error_short_label(corrected_error_details)
            
            # On lance l'apprentissage (ajoute au CSV + lance train.py)
            trigger_auto_learning(failed_step, browser_log, corrected_error_details)
            
            # On écrase les valeurs pour le popup immédiat
            category = f"New: {short_type}"
            priority = "HIGH"
            suggestion = f"✅ Erreur apprise automatiquement | Type : {short_type}"
        else:
            suggestion = f"Analyse confirmée à {int(confidence*100)}% par l'IA"
            
    elif not status_is_failed:
        category, priority, suggestion = "Succès", "NONE", "Test réussi avec succès."

    # 4. Envoi du rapport final au popup (Queue pour WebSocket/Frontend)
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

# --- JIRA INTEGRATION ---
@app.post("/jira/create-session-ticket")
async def create_jira_ticket(request: Request):

    data = await request.json()

    test_results = data.get("test_results", [])

    passed_count = 0
    failed_count = 0

    description_text = "h1. SmartQA Test Execution Report\n\n"

    for test in test_results:

        is_passed = test.get(
            "status",
            ""
        ).lower() in ["passed", "success"]

        if is_passed:
            passed_count += 1
            status_icon = "(/)"
        else:
            failed_count += 1
            status_icon = "(x)"

        description_text += (
            f"h3. {status_icon} "
            f"Scenario: {test.get('scenario', 'N/A')}\n"
        )

        # Steps
        if test.get("steps"):

            description_text += "||Step||Status||\n"

            for step in test["steps"]:

                step_status = (
                    step.get("status", "")
                    .lower()
                )

                if step_status == "passed":
                    s_icon = "(/)"
                elif step_status == "failed":
                    s_icon = "(x)"
                else:
                    s_icon = "(i)"

                description_text += (
                    f"|{step.get('text', '')}|"
                    f"{s_icon} {step_status}|\n"
                )

        # IA Analysis
        #ia = test.get("ia_analysis", {})

        description_text += (
            f"\n*Analyse IA:* "
            f"{test.get('suggestion', 'N/A')}\n"
            f"{test.get('analysis', 'N/A')}\n"
        )

        description_text += (
            f"*Détails de l'erreur:* "
            f"{test.get('corrected_error_details', 'No details')}\n"
        )

        description_text += "----\n"

    total_tests = len(test_results)
    description_text += ( 
        "\n*JSON Report Attached:* " 
        "session_data.json\n" 
    )

    jira_auth = (
        JIRA_EMAIL,
        JIRA_API_TOKEN
    )

    url = (
        f"https://{JIRA_DOMAIN}"
        "/rest/api/2/issue"
    )

    payload = {
        "fields": {

            "project": {
                "key": JIRA_PROJECT_KEY
            },

            "summary": (
                "QA Test Execution - "
                f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ),

            "description": description_text,

            "issuetype": {
                "name": "Test Execution"
            },

            "customfield_10109": total_tests, 
            "customfield_10104": passed_count, 
            "customfield_10105": failed_count,

            "labels": [
                "selenium",
                "automation",
                "smartqa"
            ]

           
        }
    }

    async with httpx.AsyncClient(
        timeout=60.0
    ) as client:

        # Create Jira ticket
        resp = await client.post(
            url,
            json=payload,
            auth=jira_auth
        )

        if resp.status_code != 201:

            logger.error(
                f"Jira Error: {resp.text}"
            )

            return {
                "success": False,
                "error": resp.text
            }

        issue_key = resp.json()["key"]

        logger.info(
            f"Ticket créé : {issue_key}"
        )

        try:
           json_str = json.dumps(data, indent=4, ensure_ascii=False)
           attach_url = f"https://{JIRA_DOMAIN}/rest/api/2/issue/{issue_key}/attachments"
           print("ATTACH URL:", attach_url)

           # 2. Headers cruciaux pour l'API Jira
           headers = {
             "X-Atlassian-Token": "no-check",
             "Accept": "application/json"
           }

           files = {
              "file": ("session_data.json", io.BytesIO(json_str.encode('utf-8')), "application/json")
           }

           # 4. Envoi de la requête
           attach_resp = await client.post(
               attach_url,
               headers=headers,
               files=files,
               auth=jira_auth
           )

           if attach_resp.status_code == 200:
              logger.info(f"Fichier attaché avec succès ! Status: {attach_resp.status_code}")
           else:
              logger.error(f"Échec de l'upload. Status: {attach_resp.status_code}, Réponse: {attach_resp.text}")
        except Exception as e:
           logger.error(f"Erreur lors de l'attachement JSON: {e}", exc_info=True)

        # Upload screenshots
        for idx, test in enumerate(test_results):

            if test.get("screenshot"):

                await upload_screenshot_to_jira(
                    client,
                    issue_key,
                    test["screenshot"],
                    f"screenshot_{idx}.png",
                    jira_auth
                )

        return {
            "success": True,
            "issueKey": issue_key,
            "passed": passed_count,
            "failed": failed_count,
            "total": total_tests
        }


async def upload_screenshot_to_jira(
    client,
    issue_key,
    b64_string,
    filename,
    auth
):

    try:

        if "base64," in b64_string:
            b64_string = (
                b64_string
                .split("base64,")[1]
            )

        image_data = base64.b64decode(
            b64_string
        )

        url = (
            f"https://{JIRA_DOMAIN}"
            f"/rest/api/2/issue/"
            f"{issue_key}/attachments"
        )

        headers = {
            "X-Atlassian-Token": "no-check"
        }

        files = {
            "file": (
                filename,
                image_data,
                "image/png"
            )
        }

        resp = await client.post(
            url,
            headers=headers,
            files=files,
            auth=auth
        )

        logger.info(
            f"Screenshot upload status: "
            f"{resp.status_code}"
        )

    except Exception as e:

        logger.error(
            f"Screenshot upload error: {e}",
            exc_info=True
        )



# --- xray ---

async def get_xray_token():

    url = f"{XRAY_BASE_URL}/authenticate"

    payload = {
        "client_id": XRAY_CLIENT_ID,
        "client_secret": XRAY_CLIENT_SECRET
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload)

        if resp.status_code != 200:
            raise Exception(resp.text)

        return resp.text.replace('"', '')


async def search_test(client, scenario):

    url = f"{JIRA_BASE_URL}/rest/api/2/search"

    jql = f'project = {JIRA_PROJECT_KEY} AND issuetype = Test AND summary ~ "{scenario}"'

    resp = await client.get(
        url,
        params={"jql": jql, "maxResults": 1},
        auth=(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    issues = resp.json().get("issues", [])

    if issues:
        return issues[0]["key"]

    return None

import httpx

async def create_test_with_steps(token, test):
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

    # Configuration explicite d'un timeout global (60s pour la lecture et la connexion)
    # Cela évite que httpx n'utilise ses valeurs par défaut (5s) en tâche de fond.
    timeout_config = httpx.Timeout(60.0, read=60.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout_config) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            
            print("STATUS:", resp.status_code)
            print("RESPONSE:", resp.text)

            if resp.status_code != 200:
                raise Exception(resp.text)

            data = resp.json()

            if "errors" in data:
                raise Exception(data["errors"])

            test_data = data["data"]["createTest"]["test"]
            return test_data.get("issueId")
            
        except httpx.ReadTimeout:
            print(f"[TIMEOUT] L'API Xray a mis trop de temps à répondre pour le scénario: {scenario}")
            raise Exception("Xray API Read Timeout - Serveur surchargé ou latence réseau importante.")

async def execute_tests(token, tests):
    url = "https://eu.xray.cloud.getxray.app/api/v2/import/execution"

    cleaned_tests_payload = []
    for t in tests:
        test_key = t.get("testKey")
        if not test_key:
            continue
            
        status_raw = t.get("status", "").lower()
        status_final = "PASSED" if status_raw in ["passed", "success"] else "FAILED"

        # Construction du bloc pour un test
        test_entry = {
            "testKey": str(test_key),
            "status": status_final,
            "comment": str(t.get("analysis", ""))
        }

        # CORRECTION : Si un bug a été créé pour ce test, on transmet sa clé à Xray
        if "defectKey" in t:
            test_entry["defects"] = [t["defectKey"]]  # Xray liera ce bug comme un Défaut !

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

    url = f"{JIRA_BASE_URL}/rest/api/2/issue"

    steps = "\n".join([
        f"- {s.get('text')} ({s.get('status')})"
        for s in test.get("steps", [])
    ])

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": f"[BUG] {test.get('scenario')}",

            "description": f"""
Scenario:
{test.get('scenario')}

Steps:
{steps}

AI Analysis:
{test.get('analysis',''), test.get('suggestion','')}

""",

            "issuetype": {"name": "Bug"},
            "labels": ["smartqa", "auto-bug"]
        }
    }

    resp = await client.post(
        url,
        json=payload,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    return resp.json()["key"]

async def upload_screenshot_to_bug(client, bug_key, image_data, filename="screenshot.png"):
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{bug_key}/attachments"

    # CORRECTION : Si l'image est une chaîne Base64, on la nettoie et on la décode en binaire
    if isinstance(image_data, str):
        # On retire l'en-tête "data:image/png;base64," si l'outil de test l'a inclus
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
        
        # Nettoyage des espaces ou retours à la ligne parasites
        image_data = image_data.strip()
        
        # Conversion de la chaîne Base64 en octets binaires réels
        try:
            binary_data = base64.b64decode(image_data)
        except Exception as e:
            print(f"[ERREUR] Échec du décodage Base64 du screenshot : {e}")
            return None
    else:
        # Si les données sont déjà binaires, on les garde telles quelles
        binary_data = image_data

    # On passe les données décodées (binary_data) à Jira
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

        # =====================================================
        # 1. CREATE OR GET TESTS (GRAPHQL + STEPS)
        # =====================================================
        for t in test_results:
            scenario = t.get("scenario")
            test_key = await search_test(client, scenario)

            if not test_key:
                new_tests_created = True
                issue_id = await create_test_with_steps(token, t)
                
                try:
                    jira_url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_id}"
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

        # Temporisation pour l'indexation Xray/Jira si nécessaire
        if new_tests_created:
            print("[INFO] Pause de 4 secondes pour l'indexation Xray Cloud...")
            await asyncio.sleep(4.0)

        # =====================================================
        # 2. CORRECTION : HANDLE FAILURES & CREATE BUGS FIRST
        # =====================================================
        # On crée les bugs d'abord pour avoir leurs clés AVANT d'exécuter
        for t in enriched:
            status = t.get("status", "").lower()

            if status not in ["passed", "success"]:
                # 2.1 Création du Bug dans Jira
                bug_key = await create_bug(client, t)

                # 2.2 Copie du Screenshot sur le Bug
                screenshot = t.get("screenshot")
                if screenshot:
                    await upload_screenshot_to_bug(client, bug_key, screenshot)

                # 2.3 On associe la clé du bug au test en cours pour l'exécution Xray
                t["defectKey"] = bug_key

                bugs.append({
                    "test": t["testKey"],
                    "bug": bug_key
                })

        # =====================================================
        # 3. EXECUTE & LINK TESTS (L'API liera automatiquement les défauts)
        # =====================================================
        execution = await execute_tests(token, enriched)

        # =====================================================
        # 4. RESPONSE
        # =====================================================
        return {
            "success": True,
            "execution": execution,
            "tests": enriched,
            "bugs": bugs
        }
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)