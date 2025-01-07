
from flask import Flask, app
from blueprints.reports import reports_bp
from globals import UPLOAD_FOLDER

app = Flask(__name__)

app.register_blueprint(reports_bp)


if __name__ == "__main__":
    app.run(debug=True)