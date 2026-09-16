# 🚲 Projet Data Engineering — Vélib' & Météo à Paris

<div align="center">

<img src="https://github.com/user-attachments/assets/4f74dcb8-b636-48c9-b1fd-8dcd3b8c84fb" alt="Logo" height="120" width="210">

</div>

### 📌 Présentation

Ce projet consiste à construire un **pipeline Data Engineering end-to-end** permettant d'analyser l'influence des conditions météorologiques sur les disponibilités des stations Vélib' à Paris.

Les données sont collectées depuis les API **Open Data Paris (Vélib')** et **Open-Meteo**, puis ingérées, stockées, transformées et visualisées.

<div align="center">

<img width="3739" height="1178" alt="Pipeline tools" src="https://github.com/user-attachments/assets/54f94962-17da-4428-970f-69c1fe7f4277" />

</div>

---

## 🏗️ Architecture

```text
Vélib' API ──────┐
                 ├──► Python ──► PostgreSQL
Météo API ───────┘                  │
                                    ▼
                                   dbt
                              Transformation
                                    │
                                    ▼
                              Tables analytiques
                                    │
                                    ▼
                               Streamlit
                                Dashboard

                         ▲
                         │
                       Airflow
                      Orchestration

                    🐳 Docker
                 Conteneurisation
```

---

## 🔄 Pipeline de données

### 1. 🚲 Ingestion

Collecte automatisée des données Vélib' et météorologiques via leurs APIs à l'aide de **Python**.

### 2. 🐘 Stockage

Chargement des données brutes dans **PostgreSQL**, notamment dans les tables :

* `bronze.velib_stations`
* `bronze.meteo_paris`

### 3. 🔧 Transformation avec dbt

Nettoyage, transformation et modélisation des données avec **dbt** :

```text
stg_velib
stg_meteo
     ↓
int_velib_meteo
     ↓
fct_velib_meteo
```

Les données Vélib' et météo sont ainsi croisées pour produire une table analytique exploitable.

### 4. 🛫 Orchestration avec Airflow

**Apache Airflow** automatise et orchestre les différentes étapes du pipeline : ingestion → stockage → transformation.

### 5. 📊 Dashboard Streamlit

Une application **Streamlit** permet d'explorer les disponibilités Vélib' et leur évolution selon les conditions météorologiques.

### 6. 🐳 Docker

L'ensemble des services est **conteneurisé avec Docker et Docker Compose** afin de garantir un environnement reproductible et facilement déployable.

---

## 🛠️ Technologies

**Python · PostgreSQL · dbt · Apache Airflow · Streamlit · Docker · Docker Compose · AWS · Git/GitHub**

---

## 🎯 Objectif

Mettre en œuvre une architecture Data Engineering complète :

**API → Ingestion → PostgreSQL → dbt → Airflow → Streamlit → Docker**

avec pour objectif final de transformer des données brutes en **données analytiques exploitables**.

Par **Edgard BASSO**

