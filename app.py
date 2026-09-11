import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from agent.agent import CampusTransportAgent

load_dotenv()

app = Flask(__name__)
agent = CampusTransportAgent()

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/ask")
def ask():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Please enter a transport question."}), 400

    try:
        result = agent.run(message)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Agent error")
        return jsonify({
            "error": "The agent could not complete the request.",
            "details": str(exc)
        }), 500

@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "model": os.getenv("OPENAI_MODEL", "gpt-5.6")
    })

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1"
    )
