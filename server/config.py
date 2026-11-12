import os

from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

//inintialise flask and configure database
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql://localhost:5432/kilimorada"
).replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

#configure seesions, security and swagger
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 8  # 8 hours
app.config["TWO_FACTOR_ENABLED"] = os.environ.get("TWO_FACTOR_ENABLED", "true").lower() == "true"
app.config["SWAGGER"] = {"title": "KilimoRada API", "uiversion": 3}