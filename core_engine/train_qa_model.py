import pandas as pd
import numpy as np
import os
import pickle  # Pour sauvegarder le LabelEncoder
from datasets import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer,
    DataCollatorWithPadding,
    AutoModelForQuestionAnswering
)
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score

# --- CONFIGURATION ---
MODEL_NAME = "roberta-base"
DATASET_PATH = r"C:\Users\lenovo\Desktop\PFE 2026\Projet\Smart-QA-Assistant\core_engine\qa_dataset_v4.csv"
OUTPUT_DIR = "D:/smart_qa_v3_results"
FINAL_MODEL_PATH = "D:/smart_qa_model_final"

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

    # --- ENRICHISSEMENT DU CONTEXTE ---
    df['combined_text'] = (
        "[CONTEXT]: " + df['selenium_step'].astype(str) + 
        " | [ACTION]: " + df['user_action'].astype(str) + 
        " | [LOGS]: " + df['browser_log'].astype(str) + 
        " | [ERROR]: " + df['text'].astype(str)
    )

    # --- ENCODAGE DES LABELS ---
    df['target'] = df['label'] + "_" + df['priority']
    
    label_encoder = LabelEncoder()
    df['labels'] = label_encoder.fit_transform(df['target'])
    label_names = label_encoder.classes_.tolist()
    
    # SAUVEGARDE DE L'ENCODEUR (Essentiel pour ton API FastAPI plus tard)
    if not os.path.exists(FINAL_MODEL_PATH):
        os.makedirs(FINAL_MODEL_PATH)
    with open(os.path.join(FINAL_MODEL_PATH, "label_encoder.pkl"), "wb") as f:
        pickle.dump(label_encoder, f)

    print(f"✅ Dataset chargé : {len(df)} exemples, {len(label_names)} classes distinctes.")
    return df, label_names

def train():
    # 1. Chargement et préparation
    df, label_names = prepare_professional_data(DATASET_PATH)
    
    # Transformation en Dataset Hugging Face
    dataset = Dataset.from_pandas(df[['combined_text', 'labels']])
    
    # 2. Tokenization
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    def tokenize_fn(examples):
        # On ne met pas de padding ici, le DataCollator s'en chargera dynamiquement
        return tokenizer(examples["combined_text"], truncation=True, max_length=256)

    tokenized_datasets = dataset.map(tokenize_fn, batched=True)
    
    # 3. Split Train/Test (80/20)
    split_ds = tokenized_datasets.train_test_split(test_size=0.2, seed=42)

    # 4. Configuration du modèle
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=len(label_names),
        id2label={i: name for i, name in enumerate(label_names)},
        label2id={name: i for i, name in enumerate(label_names)}
    )
    model = AutoModelForQuestionAnswering.from_pretrained(FINAL_MODEL_PATH, low_cpu_mem_usage=True)

    # 5. Paramètres d'entraînement
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=12,
        learning_rate=2e-5, # RoBERTa préfère souvent un LR légèrement plus bas
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        warmup_steps=50,
        weight_decay=0.01,
        # Remplacement de logging_dir par logging_steps pour éviter le warning
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        report_to="none"
    )

    # 6. Initialisation du Trainer (CORRECTION DU BUG)
    # L'argument est 'processing_class' ou on passe simplement par le data_collator
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=split_ds["train"],
        eval_dataset=split_ds["test"],
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics
    )

    # 7. Lancement
    print("🚀 Début du Fine-tuning SmartQA v3...")
    trainer.train()

    # 8. Sauvegarde finale
    # On sauvegarde tout dans le même dossier pour l'API
    model.save_pretrained(FINAL_MODEL_PATH)
    tokenizer.save_pretrained(FINAL_MODEL_PATH)
    
    print(f"🏁 Modèle expert sauvegardé dans : {FINAL_MODEL_PATH}")

if __name__ == "__main__":
    train()