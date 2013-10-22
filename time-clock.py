from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from config import DATABASE_URI
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URI']

if __name__ == "__main__":
    app.run()
