import pandas as pd
import numpy as np
import os
import datetime
import pickle
import shutil
import gc
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer,
    DataCollatorWithPadding
)
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score

# --- CONFIGURATION ---
MODEL_NAME = "roberta-base"
DATASET_PATH = r"C:\Users\lenovo\Desktop\PFE 2026\Projet\Smart-QA-Assistant\core_engine\qa_dataset_v4.csv"
# Utiliser un dossier temporaire local pour éviter les verrous réseau/disque externe durant l'init
TEMP_OUTPUT_DIR = "./temp_training_results" 
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
FINAL_MODEL_PATH = f"D:/smart_qa_model_final_{timestamp}"

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels, predictions)
    f1 = f1_score(labels, predictions, average="weighted")
    return {"accuracy": acc, "f1": f1}

def prepare_professional_data(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Le fichier {csv_path} est introuvable.")

    df = pd.read_csv(csv_path).fillna("None")

    df['combined_text'] = (
        "[CONTEXT]: " + df['selenium_step'].astype(str) + 
        " | [ACTION]: " + df['user_action'].astype(str) + 
        " | [LOGS]: " + df['browser_log'].astype(str) + 
        " | [ERROR]: " + df['text'].astype(str)
    )

    df['target'] = df['label'] + "_" + df['priority']
    
    label_encoder = LabelEncoder()
    df['labels'] = label_encoder.fit_transform(df['target'])
    label_names = label_encoder.classes_.tolist()
    
    return df, label_names, label_encoder

def train():
    # 0. Nettoyage de la mémoire avant de commencer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 1. Chargement et préparation
    df, label_names, label_encoder = prepare_professional_data(DATASET_PATH)
    dataset = Dataset.from_pandas(df[['combined_text', 'labels']])
    
    # 2. Tokenization
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    def tokenize_fn(examples):
        return tokenizer(examples["combined_text"], truncation=True, max_length=256)

    tokenized_datasets = dataset.map(tokenize_fn, batched=True)
    split_ds = tokenized_datasets.train_test_split(test_size=0.2, seed=42)

    # 3. Configuration du modèle
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=len(label_names),
        id2label={i: name for i, name in enumerate(label_names)},
        label2id={name: i for i, name in enumerate(label_names)}
    )

    # 4. Paramètres d'entraînement
    training_args = TrainingArguments(
        output_dir=TEMP_OUTPUT_DIR, # On travaille en local d'abord
        num_train_epochs=12,
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        warmup_steps=50,
        weight_decay=0.01,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        report_to="none",
        save_total_limit=2 # Évite de remplir le disque avec trop de checkpoints
    )

    # 5. Initialisation du Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=split_ds["train"],
        eval_dataset=split_ds["test"],
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics
    )

    # 6. Lancement
    print("🚀 Début du Fine-tuning SmartQA...")
    trainer.train()

    # 7. SAUVEGARDE SÉCURISÉE (On évite le conflit I/O)
    print("📦 Préparation de la sauvegarde finale...")
    
    # Créer le dossier final s'il n'existe pas
    if not os.path.exists(FINAL_MODEL_PATH):
        os.makedirs(FINAL_MODEL_PATH)

    # Sauvegarder l'encodeur
    with open(os.path.join(FINAL_MODEL_PATH, "label_encoder.pkl"), "wb") as f:
        pickle.dump(label_encoder, f)

    # Sauvegarde du modèle et tokenizer
    # On utilise un bloc try/except pour voir si Windows bloque encore
    try:
        trainer.save_model(FINAL_MODEL_PATH)
        tokenizer.save_pretrained(FINAL_MODEL_PATH)
        print(f"🏁 Modèle expert sauvegardé avec succès dans : {FINAL_MODEL_PATH}")
    except Exception as e:
        print(f"⚠️ Erreur de sauvegarde directe : {e}")
        print("🔄 Tentative de copie manuelle...")
        # Si save_model échoue à cause d'un verrou, on copie les fichiers du dernier checkpoint
        last_checkpoint = trainer.state.best_model_checkpoint
        if last_checkpoint:
            shutil.copytree(last_checkpoint, FINAL_MODEL_PATH, dirs_exist_ok=True)
            tokenizer.save_pretrained(FINAL_MODEL_PATH)
            print(f"🏁 Sauvegarde effectuée via copie du checkpoint : {FINAL_MODEL_PATH}")

    # 8. Nettoyage final
    if os.path.exists(TEMP_OUTPUT_DIR):
        shutil.rmtree(TEMP_OUTPUT_DIR, ignore_errors=True)

if __name__ == "__main__":
    train()