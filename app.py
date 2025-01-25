from flask import Flask, session

app = Flask(__name__)
app.secret_key = "123456789"
app.config["SESSION_TYPE"] = "filesystem"

from blueprints.index import bp as index_bp
from blueprints.learn import bp as learn_bp
from blueprints.chat import bp as chat_bp

app.register_blueprint(index_bp)
app.register_blueprint(learn_bp)
app.register_blueprint(chat_bp)

if __name__ == "__main__":
    app.run(debug=True)