# news_to_mongodb.py
from newsapi import NewsApiClient
from pymongo import MongoClient
from newspaper import Article

import datetime
import time

# ------------------------------
# CONFIGURATION
# ------------------------------

API_KEY = "a95ec8f0ed5b44ce8f36fcd10e864da5"  # Remplace par ta clé NewsAPI
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "news_db"
COLLECTION_NAME = "articles"

# Pays à récupérer (ISO 2 lettres)
countries = ["us", "gb", "fr", "de", "in"]

# Sources à récupérer (IDs NewsAPI)
sources = [
    "bbc-news",
    "cnn",
    "the-verge",
    "cbs-news",
    "reuters",
    "al-jazeera-english",
]

# Mots-clés pour get_everything
keywords = ["AI", "technology", "politics", "economy", "health"]

# Nombre max d'articles par requête (max 100)
PAGE_SIZE = 100

# ------------------------------
# INITIALISATIONS
# ------------------------------

# MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# NewsAPI
newsapi = NewsApiClient(api_key=API_KEY)

# Définir la période : récupérer les news des 7 derniers jours
today = datetime.date.today()
from_date = today - datetime.timedelta(days=7)


# ------------------------------
# FONCTION DE NETTOYAGE
# ------------------------------
def clean_article(article):
    """Conserve uniquement les champs utiles"""
    return {
        "title": article.get("title"),
        "description": article.get("description"),
        "content": article.get("content"),
        "url": article.get("url"),
        "image": article.get("urlToImage"),
        "publishedAt": article.get("publishedAt"),
        "source": article.get("source", {}).get("name"),
    }


def extract_full_article(article_doc):
    """
    Prend un document existant depuis MongoDB (avec un champ 'url'),
    télécharge et extrait le contenu complet de l'article.
    Met ensuite à jour le document.
    """
    url = article_doc["url"]
    try:
        # Charger l'article
        article = Article(
            url, language="en"
        )  # change en "ar" ou "fr" si nécessaire
        article.download()
        article.parse()

        # Mettre à jour le doc avec le texte complet
        collection.update_one(
            {"_id": article_doc["_id"]},
            {"$set": {"full_content": article.text}},
        )

        print(
            f"[OK] Article complet récupéré : {article_doc['title'][:50]}..."
        )
    except Exception as e:
        print(f"[Erreur] Impossible d'extraire {url} : {e}")


# ------------------------------
# COLLECTE DES ARTICLES
# ------------------------------
all_articles = []

for country in countries:
    for source in sources:
        for keyword in keywords:
            try:

                print(
                    f"Récupération : country={country}, "
                    f"source={source}, keyword={keyword}"
                )

                response = newsapi.get_everything(
                    q=keyword,
                    sources=source,
                    from_param=from_date,
                    to=today,
                    language="en",
                    sort_by="publishedAt",
                    page_size=PAGE_SIZE,
                )

                articles = response.get("articles", [])
                for article in articles:
                    cleaned = clean_article(article)

                    # Eviter doublons via URL
                    if not collection.find_one({"url": cleaned["url"]}):
                        collection.insert_one(cleaned)
                        all_articles.append(cleaned)

                # Pause pour respecter la limite d'API
                time.sleep(1)

            except Exception as e:
                print(f"Erreur : {e}")
                continue

print(f"Total articles récupérés et insérés : {len(all_articles)}")
