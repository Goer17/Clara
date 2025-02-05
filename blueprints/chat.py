import os, random, time
from flask import Blueprint, render_template, session, request, jsonify

bp = Blueprint('chat', __name__, url_prefix='/chat')

from agent.retriever import Retriever
from agent.generator import Generator
from agent.planner import Planner

from utils.general import (
    gpt_4o,
    ds_chat, ds_reasoner,
    tts_hd
)
from pathlib import Path

import json, re

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

from utils.questions import Quiz

# Quiz
cur_quiz: Quiz = None

@bp.route("/quiz/start", methods=["GET", "POST"])
def start():
    global cur_quiz
    if cur_quiz is not None:
        return jsonify({"error": "There is one ongoing quiz yet to be completed."}), 500
    data = request.json
    name = data.get("name")
    filepath = Path("material") / "quiz" / f"{name}.json"
    cur_quiz = Quiz.load(filepath, retriever)
    cur_quiz.init_cards()
    if isinstance(cur_quiz, Quiz):
        return jsonify({"reply": "Successfully started the quiz!"}), 200
    return jsonify({"error": "Failed starting the quiz."}), 500

@bp.route("/quiz/card", methods=["GET", "POST"])
def card():
    global cur_quiz
    if cur_quiz is None:
        return jsonify({"error": "Quiz has not been started."}), 400
    data = request.json
    try:
        idx = data.get("idx")
        cd = cur_quiz.card(idx)
        return jsonify(cd), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/quiz/mark", methods=["GET", "POST"])
def mark():
    global cur_quiz
    if cur_quiz is None:
        return jsonify({"error": "Quiz has not been started."}), 400
    data = request.json
    try:
        q_type = data["q_type"]
        idx = data["idx"]

        answer = data.get("answer", "")
        question = cur_quiz.problemset[q_type][idx]
        score, analysis, _ = question.mark(answer, gpt_4o)
        reply = {
            "score": score,
            "solution": question.solution,
            "analysis": analysis
        }
        return jsonify(reply), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/quiz/play", methods=["GET", "POST"])
def play():
    data = request.json
    content, t = data.get("content"), data.get("t")
    voice = random.choice(['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'])
    name = tts_hd.generate(content, voice)
    for _ in range(t):
        time.sleep(2)
        tts_hd.play(name)
    
    return jsonify({"reply": "ok"}), 200

@bp.route("quiz/quit", methods=["GET", "POST"])
def quit():
    global cur_quiz
    cur_quiz = None
    
    return jsonify({"reply": "you quited this task!"}), 200

@bp.route("/quiz/end", methods=["GET", "POST"])
def end():
    global cur_quiz
    cur_quiz = None
    
    # TODO summarize
    
    return jsonify({"reply": "The current quiz was completed!"}), 200

@bp.route("/clear_cache", methods=["GET", "POST"])
def clear_cache():
    # TODO
    pass