import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
GEMINI_API_KEY = "AIzaSyABcdZqp5FYzjKqQYEJc234YDbd123Uxa8"
GEMINI_API_URL = "https://aistudio.google.com/apikey"

@app.route('/chatbot-gemini', methods=['POST'])
def chatbot_gemini():
    data = request.json
    user_message = data.get('message', '')
    project_context = data.get('context', '')
    prompt = f"User: {user_message}\nProject Data: {project_context}\nAssistant:"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    try:
        resp = requests.post(GEMINI_API_URL, json=payload)
        resp.raise_for_status()
        gemini_reply = resp.json()['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"reply": gemini_reply})
    except Exception as e:
        return jsonify({"reply": "Sorry, I couldn't reach Gemini API. (" + str(e) + ")"}), 500

if __name__ == '__main__':
    app.run(debug=True)
