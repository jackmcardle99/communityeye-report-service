from flask import Flask
from blueprints.reports.reports import reports_bp
from flask_cors import CORS
from config import FLASK_DEBUG, FLASK_HOST, FLASK_PORT
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(reports_bp)
    return app


app = create_app()

if __name__ == "__main__":
    logger.info(
        f"Starting Flask app on {FLASK_HOST}:{FLASK_PORT} with debug={FLASK_DEBUG}"
    )
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT)
