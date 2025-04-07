from flask import Flask, session

app = Flask(__name__)
app.secret_key = "clara"
app.config["SESSION_TYPE"] = "filesystem"

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from blueprints.index import bp as index_bp
from blueprints.learn import bp as learn_bp
from blueprints.chat import bp as chat_bp
from blueprints.notebook import bp as notebook_bp
from blueprints.setting import bp as setting_bp

app.register_blueprint(index_bp)
app.register_blueprint(learn_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(notebook_bp)
app.register_blueprint(setting_bp)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8088)