from app import app
from config import Config

# Import routes for gunicorn (must be at module level)
import routes

if __name__ == '__main__':
    app.run(debug=Config.FLASK_DEBUG, host=Config.SERVER_HOST, port=Config.SERVER_PORT)