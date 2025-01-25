from flask import Blueprint, render_template, session, request, jsonify

bp = Blueprint('chat', __name__, url_prefix='/chat')

from agent.retriever import Retriever
from agent.generator import Generator
from agent.planner import Planner

from utils.general import (
    gpt_4o, tts_hd
)

retriever = Retriever(gpt_4o)
generator = Generator(gpt_4o)
planner = Planner(gpt_4o, retriever, generator)

@bp.route("/v1", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message")
    if message is None:
        return jsonify({"error": "Message is empty!"}), 400
    if "chat_history" not in session:
        session["chat_history"] = []
    session["chat_history"].append(
        {
            "role": "user",
            "content": message
        }
    )
    try:
        response = planner.chat(session["chat_history"])
        session["chat_history"].append(
            {
                "role": "assistant",
                "content": response
            }
        )
        session.modified = True
        
        return jsonify({"reply": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("reset", methods=["POST"])
def reset():
    session["chat_history"] = []
    return jsonify({"system": "chat history was cleared."}), 200