
from flask import Flask, app
from blueprints.reports import reports_bp
from globals import UPLOAD_FOLDER
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.register_blueprint(reports_bp)


if __name__ == "__main__":
    app.run(debug=True)