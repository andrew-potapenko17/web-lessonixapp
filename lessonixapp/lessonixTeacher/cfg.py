from dotenv import load_dotenv
import os

load_dotenv()

cfg = {
    "apiKey": os.getenv("DB_API_KEY"),
    "authDomain": os.getenv("DB_AUTH_DOMAIN"),
    "databaseURL": os.getenv("DB_URL", "/"),
    "projectId": os.getenv("DB_PROJECT_ID"),
    "storageBucket": os.getenv("DB_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("DB_MESSAGING_SENDER_ID"),
    "appId": os.getenv("DB_APP_ID"),
}