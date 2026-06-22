import subprocess
import time
import os
import sys
import signal
MAVEN_BINARY = r"C:\Program Files\apache-maven-3.9.15\bin\mvn.cmd"
JAVA_PROJECT_PATH = r"C:\Users\lenovo\Desktop\PFE 2026\Projet\Smart-QA-Assistant\gherkin-QA\demo"
BACKEND_SCRIPT = "core_engine/main.py"
def start_pipeline():
    print("🚀 --- DÉMARRAGE DU PIPELINE SMARTQA ---")
    #Lancement du Serveur(FastAPI)
    print("📡 [1/2] Initialisation du serveur IA (FastAPI)...")
    try:
        backend_proc = subprocess.Popen([sys.executable, BACKEND_SCRIPT])
        print(f"✅ Serveur lancé avec le PID: {backend_proc.pid}")
    except Exception as e:
        print(f"❌ Erreur critique lors du lancement du serveur : {e}")
        return
    print("⏳ Attente du chargement du modèle (8s)...")
    time.sleep(20) 
    #Lancement des tests Cucumber
    print(f"🧪 [2/2] Exécution des tests Cucumber dans : {JAVA_PROJECT_PATH}")   
    try:
        result = subprocess.run(
         [MAVEN_BINARY, "test", "-Dtest=CucumberRunnerTest"],
         shell=True,
         cwd=JAVA_PROJECT_PATH 
        )
        print("\n✅ TOUS LES TESTS SONT PASSÉS !")    
    except subprocess.CalledProcessError:
        print("\n⚠️ ÉCHEC DE CERTAINS TESTS.")
        print("💡 L'IA a intercepté l'erreur et traite le diagnostic (Jira/Popup)...")
    except Exception as e:
        print(f"❌ Erreur système imprévue : {e}")
    finally:
        print("\n🏁 Pipeline terminé.")
        print("📌 Note : Le serveur reste actif. Appuyez sur CTRL+C pour l'arrêter.")
if __name__ == "__main__":
    try:
        start_pipeline()
    except KeyboardInterrupt:
        print("\n🛑 Pipeline arrêté manuellement.")