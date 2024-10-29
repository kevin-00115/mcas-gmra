#import files
from flask import Flask, render_template, request, jsonify
import openai
import os
from dotenv import load_dotenv



# Load environment variables from .env file
load_dotenv()
app = Flask(__name__)

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_completion(prompt,context,model="gpt-4o-mini"):
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
    "I'm concerned about your safety. Please know that you're not alone. Contact emergency services or call/text 988 for immediate support (US National Suicide Prevention Lifeline)."
    """
    
    messages = [
        {"role": "system", "content": therapeutic_guidelines},
        {"role": "system", "content": f"Additional context from knowledge base: {context}"},
        {"role": "user", "content": prompt}
    ]
    
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,  # Slightly higher temperature for more empathetic responses
    )
    return response.choices[0].message.content

# Flask route for the home page
@app.route("/")
def home():
    return render_template("index.html")

# Flask route to get the bot's response
@app.route("/get")
def get_bot_response():
    userText = request.args.get('msg')
    response = get_completion(userText)
    return response

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    response = get_completion(user_input)
    return jsonify({"response": response})

# Run the app
if __name__ == "__main__":
    app.run(debug=True)