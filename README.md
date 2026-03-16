# Hackathon Doc AI – Airflow Orchestration

## 1. Objectif

Ce projet implémente une plateforme d'analyse automatique de documents administratifs.

Le pipeline permet de :

* uploader des documents
* exécuter un OCR
* classifier les documents
* extraire les champs clés
* valider les règles métier
* stocker les résultats dans MongoDB

Apache Airflow est utilisé pour **orchestrer le pipeline documentaire**.

---

# 2. Installation d'Airflow

### 2.1 Prérequis

* Python 3.10+
* pip
* WSL ou Linux recommandé

---

### 2.2 Cloner le projet

```bash
git clone https://github.com/EddyTerosier/hackathon-doc-ai.git
cd hackathon-doc-ai
```

---

### 2.3 Créer un environnement Python

```bash
python3 -m venv airflow
source airflow/bin/activate
```

---

### 2.4 Installer Airflow

```bash
pip install apache-airflow
```

Vérifier l'installation :

```bash
airflow version
```

---

# 3. Initialisation d'Airflow

Définir le dossier Airflow du projet :

```bash
export AIRFLOW_HOME=$(pwd)/airflow
```

Initialiser la base :

```bash
airflow db init
```

---

# 4. Lancer Airflow

Airflow peut être lancé avec une commande tout-en-un :

```bash
airflow standalone
```

Cela lance automatiquement :

* API server (interface web)
* scheduler
* triggerer
* base de données interne

---

# 5. Accéder à l'interface

Interface Airflow :

```
http://localhost:8080
```

Le mot de passe admin est stocké dans :

```
airflow/simple_auth_manager_passwords.json.generated
```

Pour l'afficher :

```bash
cat airflow/simple_auth_manager_passwords.json.generated
```

---

# 6. Vérifier que Airflow fonctionne

Lister les DAG :

```bash
airflow dags list
```

---

# 7. Architecture Airflow du projet

Le pipeline orchestré par Airflow suit le flux suivant :

```
upload
   ↓
ocr_task (Tesseract / EasyOCR)
   ↓
classification_task
   ↓
extraction_task (SIRET / TVA / IBAN / dates)
   ↓
validation_task
   ↓
store_mongo (MongoDB / Data Lake)
   ↓
API FastAPI
   ↓
Frontend React
```

Chaque étape correspond à une tâche du DAG.

---

# 8. Structure du projet

Dans le repository :

```
backend/
    airflow/
        dags/
            document_pipeline.py
        tasks/
            ocr_task.py
            classify_task.py
            extract_task.py
            validate_task.py
            store_mongo.py
```

---

# 9. Commandes utiles

Lister les DAG :

```bash
airflow dags list
```

Afficher un DAG :

```bash
airflow dags show document_pipeline
```

Relancer Airflow :

```bash
airflow standalone
```

---


