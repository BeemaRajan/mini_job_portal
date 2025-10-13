from flask import Flask

# __name__ is the package name - 'app', for locating templates and static files
app = Flask(__name__)

from app import customers