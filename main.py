from app import app
from config import Config

# Import routes for gunicorn (must be at module level)
import routes

# Register Flask Blueprints after routes are imported
from blueprints.auth import auth_bp
from blueprints.holidays import holidays_bp
from blueprints.dashboard import dashboard_bp

app.register_blueprint(auth_bp)
app.register_blueprint(holidays_bp)
app.register_blueprint(dashboard_bp)

if __name__ == '__main__':
    app.run(debug=Config.FLASK_DEBUG, host=Config.SERVER_HOST, port=Config.SERVER_PORT)