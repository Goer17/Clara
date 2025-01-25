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

@bp.route("/reset", methods=["POST"])
def reset():
    session["chat_history"] = []
    return jsonify({"system": "chat history was cleared."}), 200

from utils.dictionary import (
    LLMDictionary, to_text
)

dic = LLMDictionary(gpt_4o)

@bp.route("/dictionary", methods=["POST"])
def dictionary():
    data = request.json
    word = data.get("word")
    words = retriever.match_node({"label": "word", "abstract": word})
    if len(words) > 0:
        return jsonify({"reply": words[0].get_prop("content")}), 200
    u_words = retriever.match_node({"label": "unfamiliar_word", "abstract": word})
    if len(u_words) > 0:
        return jsonify({"reply": u_words[0].get_prop("content")}), 200
    if word is None:
        return jsonify({"error": "Word is empty!"}), 400
    try:
        content = to_text(dic(word))
        if content is None:
            raise RuntimeError(f"Word '{word}' doesn't exist.")
        return jsonify({"reply": content}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/remember", methods=["POST"])
def remember():
    data = request.json
    profile = data.get("profile")
    n_rela = data.get("n_rela")
    try:
        node = retriever.remember(profile, n_rela)
        if node is None:
            raise RuntimeError(f"Failed to remember node: {profile}")
        return jsonify({"reply": f"One node was Remembered : {node}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
