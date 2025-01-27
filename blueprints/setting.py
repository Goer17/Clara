from flask import Blueprint, render_template, session, request

bp = Blueprint('setting', __name__, url_prefix='/setting')

@bp.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "setting/index.html"
    )
