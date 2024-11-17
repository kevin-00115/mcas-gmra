from pymongo import MongoClient
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import logging

logger = logging.getLogger('chat_history')
logger.setLevel(logging.INFO)

# create a file handler
file_handler = logging.FileHandler('chat_history.log')
file_handler.setLevel(logging.INFO)

# create a logging format and add to handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# add the handler to the logger
logger.addHandler(file_handler)

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
        # Log the message
        logger.info(f"Stored message {message} and response {response} in chat history")
    
    def get_conversation_history(self, username):
        return list(self.chats.find({"sender": username}))

    def store_document(self, document):
        return self.documents.insert_one({'document': document})

    def get_all_documents(self):
        return [doc['document'] for doc in self.documents.find({}, {'_id': 0, 'content': 1})]