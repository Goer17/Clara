import os
from pathlib import Path

from flask import Blueprint, render_template, session, request

bp = Blueprint('learn', __name__, url_prefix='/learn')

@bp.route("/", methods=["GET", "POST"])
def index():
    task_path = Path("material") / "quiz"
    if not os.path.exists(task_path):
        os.makedirs(task_path)
    task_list = []
    for task in os.listdir(task_path):
        if task.endswith(".json"):
            task_list.append(task.removesuffix(".json"))
    return render_template(
        "learn/index.html", task_list=task_list
    )

@bp.route("/task", methods=["GET", "POST"])
def task():
    name = request.args.get("name")
    return render_template(
        "learn/task.html", name=name
    )