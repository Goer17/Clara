from flask import Blueprint, render_template, session, request

bp = Blueprint('notebook', __name__, url_prefix='/notebook')

@bp.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "notebook/index.html"
    )
