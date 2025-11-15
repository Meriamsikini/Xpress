import os
import textwrap
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# 🔹 Charger les variables d'environnement
load_dotenv()
ATLAS_URI = os.getenv("MONGO_ATLAS_URI")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 🔹 Connexion MongoDB local
LOCAL_URI = "mongodb://localhost:27017"
local_client = MongoClient(LOCAL_URI)
local_db = local_client["news_db"]
articles_collection = local_db["articles"]

# 🔹 Connexion MongoDB Atlas (TLS forcé)
atlas_client = MongoClient(
    ATLAS_URI, tls=True, tlsAllowInvalidCertificates=True
)
atlas_db = atlas_client["news_db"]
embeddings_collection = atlas_db["news_embeddings"]

# 🔹 Initialiser Google Embeddings
embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", task_type="semantic_similarity"
)


# 🔹 Fonction pour découper le texte
def chunk_text(text, max_chars=1500):
    return textwrap.wrap(text, max_chars)


# 🔹 Boucle sur les articles
for article in articles_collection.find():
    text = (
        f"{article['title']}\n\n"
        f"{article.get('full_content', article.get('content', ''))}"
    )

    chunks = chunk_text(text)

    for i, chunk in enumerate(chunks):
        # Générer l'embedding
        embedding = embeddings_model.embed_query(chunk)

        # Créer le document
        doc = {
            "id": f"{article['_id']}_{i}",
            "text": chunk,
            "metadata": {
                "title": article["title"],
                "source": article.get("source", ""),
                "url": article.get("url", ""),
                "publishedAt": article.get("publishedAt", ""),
            },
            "embedding": embedding,
        }

        # Insérer dans Atlas
        embeddings_collection.insert_one(doc)

print("✅ Migration terminée avec Google Generative AI Embeddings !")
