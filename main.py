from app import app
from config import Config
import api_routes_simple

if __name__ == '__main__':
    app.run(debug=Config.FLASK_DEBUG, host=Config.SERVER_HOST, port=Config.SERVER_PORT)