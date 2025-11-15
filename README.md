# Press — Assistant d'actualités (FastAPI + MongoDB + Gemini)

Description
-----------
Application web qui combine recherche de similarité (embeddings) et génération de texte (RAG) pour répondre à des questions sur des articles d'actualité. Backend en FastAPI, stockage des embeddings et historiques dans MongoDB Atlas, LLM/embeddings via l'API Google Generative (Gemini).

Prérequis
---------
- Python 3.10+
- MongoDB Atlas avec un index Atlas Search (nom attendu : `news_index`) et collection `news_embeddings`
- Clé API Google Generative (Gemini + embeddings)
- Node/npm (optionnel si modification frontend)

Variables d'environnement
-------------------------
Créer un fichier `.env` (ne pas committer) avec au moins :
- MONGO_ATLAS_URI="mongodb+srv://.../...?retryWrites=true&w=majority"
- GOOGLE_API_KEY="VOTRE_CLE_GOOGLE"
(autres variables éventuelles selon déploiement)

Installation
------------
1. Créer et activer un virtualenv :
   python -m venv .venv
   source .venv/bin/activate  (ou .\.venv\Scripts\activate sur Windows)
2. Installer dépendances (exemple) :
   pip install fastapi uvicorn pymongo python-dotenv passlib[jwt] jinja2 langchain-google-genai

Remarque : adapter la liste des paquets selon l'implémentation réelle.

Lancement en développement
--------------------------
uvicorn main:app --reload --host 0.0.0.0 --port 8000

Accéder ensuite à : http://localhost:8000/

Structure importante du projet
------------------------------
- main.py : backend FastAPI, routes :
  - GET /register, POST /register
  - GET /login, POST /login
  - GET / (page d'accueil)
  - POST /ask?email=... (RAG + sauvegarde historique)
  - GET /history?email=...
  - DELETE /history?email=...&id=...
  - POST /history (fallback suppression)
- static/ : fichiers JS/CSS (ex. static/app.js)
- templates/ : pages Jinja2 (index.html, login.html, register.html)
- Utilisateurs stockés dans `users` collection ; historiques dans `historiques`.

Front-end
---------
- static/app.js gère l'UI : envoi de questions vers /ask, gestion du sidebar historique, suppression via DELETE ou fallback POST, thème clair/sombre stocké en localStorage, authentification basique via email enregistré en localStorage.
- Les appels client attendent un paramètre `email` (ex. /ask?email=user@example.com).

Points d'attention & dépannage
------------------------------
- Atlas Search : pour KNN sur embeddings vous devez créer un index Vector Search (nommé `news_index`) pointant vers le champ `embedding`.
- Modèles et noms utilisés dans main.py : `models/text-embedding-004` pour embeddings et `gemini-2.5-flash` pour generation ; adapter si nécessaire.
- Vérifier que MONGO_ATLAS_URI et GOOGLE_API_KEY sont correctement définis.
- Si DELETE renvoie 405, le client essaie un POST fallback (/history with action=delete).
- Ne commitez jamais vos clés/API dans le dépôt.

Sécurité
--------
- Stockage minimal des mots de passe : la démo utilise argon2 (passlib) pour le hash. En production, ajouter vérifications, validation d'email, CSRF, HTTPS et règles CORS appropriées.
