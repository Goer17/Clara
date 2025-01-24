from flask import Blueprint, render_template, session, request

bp = Blueprint('learn', __name__, url_prefix='/learn')

@bp.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "learn/index.html"
    )
