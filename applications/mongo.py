import os
from functools import lru_cache

from django.core.exceptions import ImproperlyConfigured
from pymongo import MongoClient


@lru_cache(maxsize=1)
def get_mongo_client():
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        raise ImproperlyConfigured(
            "MONGODB_URI is not configured. Copy backend/.env.example to backend/.env "
            "and set your MongoDB Atlas connection string."
        )
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def get_applications_collection():
    database_name = os.getenv("MONGODB_DATABASE", "").strip()
    if not database_name:
        raise ImproperlyConfigured(
            "MONGODB_DATABASE is not configured. Set it in backend/.env."
        )
    return get_mongo_client()[database_name]["applications"]
