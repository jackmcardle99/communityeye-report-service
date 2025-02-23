
from flask import Flask, app
from blueprints.reports import reports_bp
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.register_blueprint(reports_bp)
app.config['DEBUG'] = True 

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)