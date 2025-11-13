from app import app
from config import Config

# Import routes for gunicorn (must be at module level)
import routes

# Register tenant middleware
from middleware_tenant import load_tenant_context
app.before_request(load_tenant_context)

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
from blueprints.hr import hr_bp
from blueprints.mansioni import mansioni_bp
from blueprints.ccnl import ccnl_bp
from blueprints.admin import admin_bp
from blueprints.presidio import presidio_bp
from blueprints.export import export_bp
from blueprints.qr import qr_bp
from blueprints.interventions import interventions_bp
from blueprints.aci import aci_bp
from blueprints.api import api_bp
from blueprints.banca_ore import banca_ore_bp
from blueprints.companies import companies_bp
from blueprints.commesse import commesse_bp
from blueprints.social_safety import social_safety_bp
from blueprints.calendar import calendar_bp

# CIRCLE Blueprints
from blueprints.circle_home import bp as circle_bp
from blueprints.circle_news import bp as circle_news_bp
from blueprints.circle_communications import bp as circle_communications_bp
from blueprints.circle_groups import bp as circle_groups_bp
from blueprints.circle_polls import bp as circle_polls_bp
from blueprints.circle_calendar import bp as circle_calendar_bp
from blueprints.circle_documents import bp as circle_documents_bp
from blueprints.circle_tools import bp as circle_tools_bp
from blueprints.circle_channels import bp as circle_channels_bp

# Legal/GDPR Blueprints
from blueprints.legal import bp as legal_bp

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
app.register_blueprint(hr_bp)
app.register_blueprint(mansioni_bp)
app.register_blueprint(ccnl_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(presidio_bp)
app.register_blueprint(export_bp)
app.register_blueprint(qr_bp)
app.register_blueprint(interventions_bp)
app.register_blueprint(aci_bp)
app.register_blueprint(api_bp)
app.register_blueprint(banca_ore_bp)
app.register_blueprint(companies_bp)
app.register_blueprint(commesse_bp)
app.register_blueprint(social_safety_bp)
app.register_blueprint(calendar_bp)

# CIRCLE Blueprints
app.register_blueprint(circle_bp)
app.register_blueprint(circle_news_bp)
app.register_blueprint(circle_communications_bp)
app.register_blueprint(circle_groups_bp)
app.register_blueprint(circle_polls_bp)
app.register_blueprint(circle_calendar_bp)
app.register_blueprint(circle_documents_bp)
app.register_blueprint(circle_tools_bp)
app.register_blueprint(circle_channels_bp)

# Legal/GDPR Blueprints
app.register_blueprint(legal_bp)

# Import CLI commands
import cli_commands  # noqa: F401

if __name__ == '__main__':
    app.run(debug=Config.FLASK_DEBUG, host=Config.SERVER_HOST, port=Config.SERVER_PORT)