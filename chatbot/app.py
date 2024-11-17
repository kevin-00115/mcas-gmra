from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from database import Database
from document_processor import DocumentProcessor
from functools import wraps
import os
import openai
from dotenv import load_dotenv
import logging
from datetime import datetime
import secrets

# Load environment variables
load_dotenv()

def verify_directories():
    """Verify and create necessary directories"""
    required_dirs = ['documents', 'static', 'templates']
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for dir_name in required_dirs:
        dir_path = os.path.join(base_dir, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"Created directory: {dir_path}")
    return base_dir

# Initialize Flask app
app = Flask(__name__)
# Set up secret key
if os.getenv('FLASK_SECRET_KEY'):
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
else:
    # Generate a secure random key if none exists
    generated_key = secrets.token_hex(32)
    app.secret_key = generated_key
    # Save it to .env file if it doesn't exist
    if not os.path.exists('.env'):
        with open('.env', 'a') as f:
            f.write(f'\nFLASK_SECRET_KEY="{generated_key}"')

# Verify directories exist
base_dir = verify_directories()

# Initialize services
db = Database()
doc_processor = DocumentProcessor()

@app.before_request
def verify_documents_loaded():
    """Verify that documents are loaded into Pinecone index"""
    if not hasattr(app, 'documents_loaded'):
        print("Documents not loaded. Loading documents...")
        doc_processor.load_documents() 
        print("Documents loaded successfully.")
        app.documents_loaded = True        
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
        
    try:
        username = request.json.get("username")
        password = request.json.get("password")
        
        if not username or not password:
            return jsonify({"status": "error", "message": "Missing credentials"}), 400
        
        user = db.verify_user(username, password)
        if user:
            session['username'] = username
            return jsonify({"status": "success", "username": username})
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"status": "error", "message": "Server error"}), 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
        
    try:
        username = request.json.get('username')
        password = request.json.get('password')
        
        if not username or not password:
            return jsonify({"status": "error", "message": "Missing credentials"}), 400
        
        if db.create_user(username, password):
            session['username'] = username
            return jsonify({"status": "success", "username": username})
        return jsonify({"status": "error", "message": "Username already exists"}), 409
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"status": "error", "message": "Server error"}), 500


@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'username' in session:
        return render_template("index.html", username=session['username'])
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
#@login_required
def chat():
    try:
        user_input = request.json.get("message")
        username = session['username']
        
        if not user_input:
            return jsonify({"error": "No message provided"}), 400

        # Get chat history for context
        chat_history = db.get_conversation_history(username)
        
        # Get relevant context from documents
        context = doc_processor.query_relevant_context(user_input, chat_history)
        
        # Generate response using OpenAI
        response = get_completion(user_input, context)
        
        # Store the message and response
        db.store_message(username, user_input, response)
        
        return jsonify({
            "reply": response,
            "context": context  # Optional: Include context for debugging
        })
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": "Failed to process message"}), 500

def get_completion(prompt, context, model="gpt-4-turbo-preview"):
    try:
        therapeutic_guidelines = """You are a supportive, empathetic therapeutic assistant. Your role is to:
        - Listen actively and reflect understanding
        - Show empathy and validate feelings
        - Ask open-ended questions when appropriate
        - Help identify patterns in thoughts and feelings
        - Suggest healthy coping strategies
        - Maintain professional boundaries
        - Never provide medical advice or diagnoses
        - Encourage seeking professional help when needed
        
        If someone expresses thoughts of self-harm or suicide, ALWAYS respond with:
        "I'm concerned about your safety. Please know that you're not alone. Contact emergency services or call/text 988 for 
        immediate support (US National Suicide Prevention Lifeline)."
        """
        
        messages = [
            {"role": "system", "content": therapeutic_guidelines},
            {"role": "system", "content": f"Additional context from knowledge base: {context}"},
            {"role": "user", "content": prompt}
        ]
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return "I apologize, but I'm having trouble generating a response. Please try again."

@app.route('/history')
#@login_required
def get_history():
    try:
        username = session['username']
        history = db.get_conversation_history(username)
        return jsonify(history)
    except Exception as e:
        logger.error(f"History retrieval error: {str(e)}")
        return jsonify({"error": "Failed to retrieve history"}), 500

@app.route('/new_conversation', methods=['POST'])
#@login_required
def new_conversation():
    try:
        username = session['username']
        conversation_id = db.start_conversation(username)
        session['conversation_id'] = conversation_id
        return jsonify({
            "status": "success", 
            "conversation_id": conversation_id
        })
    except Exception as e:
        logger.error(f"New conversation error: {str(e)}")
        return jsonify({"error": "Failed to start new conversation"}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Start the application
    app.run(debug=os.getenv('FLASK_ENV') == 'development')
