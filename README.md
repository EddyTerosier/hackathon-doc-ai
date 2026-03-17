# Hackathon Doc AI – Pipeline Orchestration, Tests & Monitoring

## 1. Objectif

Ce projet implémente une plateforme d'analyse automatique de documents administratifs.

Le pipeline permet de :

* uploader des documents
* exécuter un OCR
* classifier et extraire les champs clés
* stocker les résultats dans MongoDB
* valider les règles métier
* mettre à jour le statut du document
* enregistrer les erreurs techniques et métier en base (monitoring)

Apache Airflow est utilisé pour **orchestrer le pipeline documentaire**.

---

# 2. Lancer avec Docker (recommandé)

### 2.1 Prérequis

* Docker
* Docker Compose

### 2.2 Lancer Airflow + MongoDB

```bash
docker-compose up airflow mongo -d
```

### 2.3 Accéder à l'interface

```
http://localhost:8080
```

Le mot de passe admin est généré au premier démarrage. Pour le récupérer :

```bash
docker exec -it hackathon-airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

Si l'utilisateur admin n'existe pas encore :

```bash
docker exec -it hackathon-airflow airflow users create \
  --username admin --password admin \
  --firstname Admin --lastname Admin \
  --role Admin --email admin@admin.com
```

Pour réinitialiser le mot de passe :

```bash
docker exec -it hackathon-airflow airflow users reset-password --username admin --password admin
```

### 2.4 Rebuilder après modification du code

```bash
docker-compose build airflow
docker-compose up airflow -d
```

### 2.5 Voir les logs

```bash
docker logs hackathon-airflow
docker logs hackathon-airflow 2>&1 | grep -i error
```

### 2.6 Arrêter les containers

```bash
docker-compose down
```

---

# 3. Lancer en local (dev)

### 3.1 Prérequis

* Python 3.10+
* pip
* WSL ou Linux recommandé
* MongoDB accessible sur `localhost:27017`

### 3.2 Créer un environnement Python

```bash
python3 -m venv airflow
source airflow/bin/activate
```

### 3.3 Installer les dépendances

```bash
pip install apache-airflow
pip install -r airflow/requirements.txt
```

### 3.4 Initialiser et lancer Airflow

```bash
export AIRFLOW_HOME=$(pwd)/airflow
airflow standalone
```

Le mot de passe admin est stocké dans :

```bash
cat airflow/simple_auth_manager_passwords.json.generated
```

---

# 4. Architecture du pipeline

```
ocr_task
   ↓
classify_extract_task  (classification + extraction des champs)
   ↓
store_db_task          (écriture dans MongoDB collection `documents`)
   ↓
validation_task        (règles métier)
   ↓
update_status_task     (mise à jour du statut final)
```

En cas d'échec sur n'importe quelle tâche, un **callback automatique** écrit l'erreur dans la collection MongoDB `pipeline_errors`.

---

# 5. Monitoring des erreurs

Chaque document stocké dans MongoDB contient les champs de monitoring :

```json
{
  "status": "processing",
  "pipeline_step": "store_db",
  "error": null,
  "updated_at": "..."
}
```

Les erreurs techniques (exception non gérée) sont enregistrées dans la collection `pipeline_errors` :

```json
{
  "type": "technical",
  "dag_id": "document_pipeline",
  "run_id": "...",
  "pipeline_step": "ocr_task",
  "status": "error",
  "error": "...",
  "traceback": "...",
  "occurred_at": "..."
}
```

---

# 6. Structure du projet

```
airflow/
    Dockerfile
    requirements.txt
    dags/
        document_pipeline.py
        tasks/
            ocr_task.py
            classify_extract_task.py
            store_mongo.py
            validate_task.py
            update_status_task.py
            callbacks.py
backend/
dataset/
frontend/
docker-compose.yml
```

---

# 7. Commandes utiles

Lister les DAGs :

```bash
airflow dags list
```

Afficher un DAG :

```bash
airflow dags show document_pipeline
```

Déclencher un run manuellement :

```bash
airflow dags trigger document_pipeline
```
