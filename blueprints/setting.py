from pathlib import Path
import yaml

from flask import Blueprint, render_template, session, request

bp = Blueprint('setting', __name__, url_prefix='/setting')

@bp.route("/", methods=["GET", "POST"])
def index():
    with open(Path("config") / "setting" / "generator.yml") as f:
        cfg = yaml.safe_load(f)
        model = cfg.get("model", "gpt-4o")
        temp = cfg.get("temp", 1.0)
    return render_template(
        "setting/index.html", model=model, temp=temp
    )
