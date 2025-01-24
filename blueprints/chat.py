from flask import Blueprint, render_template, session, request

bp = Blueprint('chat', __name__, url_prefix='/chat')

