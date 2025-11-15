import os
from dotenv import load_dotenv
from pymongo import MongoClient
from fastapi import FastAPI, Request, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.hash import argon2


# 🔹 Charger les variables d'environnement
load_dotenv()

ATLAS_URI = os.getenv("MONGO_ATLAS_URI")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 🔹 Connexion MongoDB Atlas
client = MongoClient(ATLAS_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["news_db"]
embeddings_collection = db["news_embeddings"]

# 🔹 Initialiser Google Embeddings
embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", task_type="semantic_similarity"
)

# 🔹 Initialiser LLM Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", api_key=GOOGLE_API_KEY, temperature=0.2
)
# gemini-1.5-flash


# 🔹 Fonction RAG : Recherche + génération
def rag_answer(user_question, k=5):
    # 1️⃣ Transformer la question en embedding
    query_embedding = embeddings_model.embed_query(user_question)

    # 2️⃣ Requête KNN dans MongoDB
    top_docs = list(
        embeddings_collection.aggregate(
            [
                {
                    "$search": {
                        "index": "news_index",
                        "knnBeta": {
                            "vector": query_embedding,
                            "path": "embedding",
                            "k": k,
                        },
                    }
                },
                {"$project": {"_id": 0, "text": 1, "metadata": 1}},
            ]
        )
    )
    print("TOP DOCS:", top_docs)  # 🔹 voir si MongoDB retourne quelque chose

    # 3️⃣ Préparer le contexte
    context = "\n\n".join(
        [
            f"Title: {doc['metadata']['title']}\nText: {doc['text']}"
            for doc in top_docs
        ]
    )

    # 4️⃣ Prompt pour le LLM
    prompt = (
        "Tu es un assistant d'actualités."
        " Utilise uniquement le contexte ci-dessous "
        "pour répondre à la question de l'utilisateur.\n"
        "Si l'information n'est pas dans le contexte, dis "
        '"Je n\'ai pas cette information dans mes sources."\n\n'
        f"Contexte :\n{context}\n\nQuestion : {user_question}\nRéponse :"
    )

    # 5️⃣ Générer la réponse
    from langchain.schema import HumanMessage

    response = llm([HumanMessage(content=prompt)])
    return response.content


# ------------------------------------
# 🔹 Variables d'environnement
load_dotenv()
ATLAS_URI = os.getenv("MONGO_ATLAS_URI")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 🔹 MongoDB
client = MongoClient(ATLAS_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["news_db"]
users_collection = db["users"]
histories_collection = db["historiques"]
embeddings_collection = db["news_embeddings"]

# 🔹 FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["\n"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# 🔹 Modèles
class User(BaseModel):
    email: str
    password: str


class Question(BaseModel):
    query: str


# 🔹 Smalltalk
smalltalk_responses = {
    "bonjour": "👋 Bonjour !",
    "salut": "Salut 👋 !",
    "comment tu vas": "Je vais très bien, merci !",
    "quelle est ta mission": "Je fournis les dernières actualités.",
    "au revoir": "À bientôt 👋 !",
    "merci": "Avec plaisir 😊 !",
}


# 🔹 Routes utilisateur
@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
def register(user: User):
    if users_collection.find_one({"email": user.email}):
        return {"error": "Utilisateur existe déjà."}
    hashed_pw = argon2.hash(user.password)
    users_collection.insert_one(
        {"email": user.email, "password": hashed_pw, "history": []}
    )
    return {"message": "Inscription réussie."}


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(user: User):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user:
        return {"error": "Utilisateur non trouvé."}
    if argon2.verify(user.password, db_user["password"]):
        return {"message": "Connexion réussie."}
    return {"error": "Mot de passe incorrect."}


@app.get("/")
def frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/history")
def get_history(email: str = Query(...)):
    # Retourne la liste des conversations
    # stockées dans la collection 'historiques'
    # pour l'email donné. Chaque élément contient
    #  un _id (string) utilisable pour la suppression.
    # chercher dans la collection historique (documents individuels avec _id)
    docs = list(histories_collection.find({"email": email}).sort("_id", -1))
    history = []
    for d in docs:
        history.append(
            {
                "_id": str(d.get("_id")),
                "question": d.get("question"),
                "answer": d.get("answer"),
                # optionnel: inclure timestamp si présent
                "created_at": (
                    d.get("created_at") if "created_at" in d else None
                ),
            }
        )
    return {"history": history}


# DELETE endpoint pour supprimer une conversation par id (ObjectId)
@app.delete("/history")
def delete_history(email: str = Query(...), id: str = Query(...)):
    if not id:
        return {"error": "Identifiant manquant."}
    try:
        oid = ObjectId(id)
    except Exception:
        return {"error": "Identifiant invalide."}

    # retrouver le document pour récupérer question/answer avant suppression
    doc = histories_collection.find_one({"_id": oid, "email": email})
    if not doc:
        return {"error": "Conversation introuvable."}

    # supprimer le document individuel
    res = histories_collection.delete_one({"_id": oid, "email": email})
    if res.deleted_count == 0:
        return {"error": "Impo de supprimer la conversation."}

    # retirer l'entrée correspondante
    # dans users_collection.history (s'il existe)
    try:
        users_collection.update_one(
            {"email": email},
            {
                "$pull": {
                    "history": {
                        "question": doc.get("question"),
                        "answer": doc.get("answer"),
                    }
                }
            },
        )
    except Exception:
        # pas bloquant : retourner succès mais log possible côté serveur
        pass

    return {"ok": True}


# POST fallback pour suppression si le client ne peut pas faire DELETE
@app.post("/history")
async def history_post(request: Request):
    data = await request.json()
    action = data.get("action")
    if action == "delete":
        email = data.get("email")
        id = data.get("id")
        return delete_history(email=email, id=id)
    return {"error": "Action non supportée."}


# 🔹 Route RAG + historique
@app.post("/ask")
def ask_question(payload: Question, email: str = Query(...)):
    user_query = payload.query.strip().lower()

    # smalltalk
    for key, response in smalltalk_responses.items():
        if key in user_query:
            answer = response
            break
    else:
        # 🔹 ici tu peux appeler rag_answer
        answer = rag_answer(
            payload.query
        )  # remplacer par rag_answer(payload.query)

    # 🔹 Sauvegarde historique
    if email:
        users_collection.update_one(
            {"email": email},
            {
                "$push": {
                    "history": {"question": payload.query, "answer": answer}
                }
            },
        )
        histories_collection.insert_one(
            {"email": email, "question": payload.query, "answer": answer}
        )

    return {"question": payload.query, "answer": answer}


# 🔹 Lancer serveur
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
