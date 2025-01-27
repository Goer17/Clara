import re
from flask import Blueprint, render_template, session, request

bp = Blueprint('index', __name__, url_prefix='/')

@bp.route("/", methods=["GET", "POST"])
def index():
    chat_history = session.get("chat_history", [])
    
    return render_template(
        "index/index.html", chat_history=chat_history
    )