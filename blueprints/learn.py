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
    mistake_path = Path("material") / "mistake"
    if not os.path.exists(mistake_path):
        os.makedirs(mistake_path)
    mistake_list = []
    for mistake in os.listdir(mistake_path):
        if mistake.endswith(".json"):
            mistake_list.append(mistake.removesuffix(".json"))
    
    return render_template(
        "learn/index.html", task_list=task_list, mistake_list=mistake_list
    )

@bp.route("/task", methods=["GET", "POST"])
def task():
    name = request.args.get("name")
    task_type = request.args.get("type", "task")
    
    place = "quiz" if task_type == "task" else "mistake"
    if not os.path.exists(Path("material") / place / f"{name}.json"):
        return render_template("learn/404.html"), 404
    
    return render_template(
        "learn/task.html", name=name, task_type=task_type
    )