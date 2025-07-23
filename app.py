from flask import Flask
from config import Config
from extensions import db, login_manager
from datetime import datetime, timezone
from dotenv import load_dotenv
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
import logging
import os
from azure.monitor.opentelemetry import configure_azure_monitor

load_dotenv()

app = Flask(__name__)

app.config.from_object(Config)

app_insights_conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if app_insights_conn_str:
    logger = logging.getLogger("britedgeLogger")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(AzureLogHandler(connection_string=app_insights_conn_str))

    middleware = FlaskMiddleware(
        app,
        exporter=AzureExporter(connection_string=app_insights_conn_str),
        sampler=ProbabilitySampler(rate=1.0),
    )

    configure_azure_monitor(logger_name="britedgeLogger")
    configure_azure_monitor(enable_live_metrics=True)
   


db.init_app(app)
login_manager.init_app(app)


login_manager.login_view = 'login'

login_manager.login_message_category = 'info'

from models import User, Job 
from routes import * 

with app.app_context():
    db.create_all()
    logger.info("Database tables created.")

@app.context_processor
def inject_now():
    return {'now': datetime.now(timezone.utc)}


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled Exception: {e}", exc_info=True)
    return "An internal error occurred.", 500


if __name__ == '__main__':
    logger.info("Starting Flask application.")
    app.run(host='0.0.0.0', debug=False, port=8080)

