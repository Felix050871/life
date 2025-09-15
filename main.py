from app import app
from config import Config

# Import routes for gunicorn (must be at module level)
import routes

# Register Flask Blueprints after routes are imported
from blueprints.auth import auth_bp
from blueprints.holidays import holidays_bp
from blueprints.dashboard import dashboard_bp
from blueprints.attendance import attendance_bp
from blueprints.shifts import shifts_bp
from blueprints.leave import leave_bp
from blueprints.messages import messages_bp
from blueprints.reperibilita import reperibilita_bp
from blueprints.reports import reports_bp
from blueprints.expense import expense_bp
from blueprints.user_management import user_management_bp
from blueprints.admin import admin_bp
from blueprints.presidio import presidio_bp
from blueprints.export import export_bp
from blueprints.qr import qr_bp
from blueprints.interventions import interventions_bp
from blueprints.aci import aci_bp
from blueprints.api import api_bp
from blueprints.banca_ore import banca_ore_bp

app.register_blueprint(auth_bp)
app.register_blueprint(holidays_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(shifts_bp)
app.register_blueprint(leave_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(reperibilita_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(expense_bp)
app.register_blueprint(user_management_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(presidio_bp)
app.register_blueprint(export_bp)
app.register_blueprint(qr_bp)
app.register_blueprint(interventions_bp)
app.register_blueprint(aci_bp)
app.register_blueprint(api_bp)
app.register_blueprint(banca_ore_bp)

if __name__ == '__main__':
    app.run(debug=Config.FLASK_DEBUG, host=Config.SERVER_HOST, port=Config.SERVER_PORT)