from pymongo import MongoClient
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["chatbot_db"]
        self.users = self.db["users"]
        self.chats = self.db["chat_history"]
        self.documents = self.db["documents"]
        
    def create_user(self, username, password):
        hashed_password = generate_password_hash(password)
        user = {
            "username": username,
            "password": hashed_password
        }
        self.users.insert_one(user)
        return user

    def verify_user(self, username, password):
        user = self.users.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            return user
        return None

    def store_message(self, sender, message, response):
        chat = {
            "sender": sender,
            "message": message,
            "response": response,
            "timestamp": datetime.now()
        }
        self.chats.insert_one(chat)
    
    def get_conversation_history(self, conversation_id):
        return self.chats.find({"conversation_id": conversation_id})

    def store_document(self, document):
        return self.documents.insert_one({'document': document})

    def get_all_documents(self):
        return [doc['document'] for doc in self.documents.find({}, {'_id': 0, 'content': 1})]