import os
from flask import (
    Flask, flash, request, redirect, url_for)
from werkzeug.utils import secure_filename
from peewee import *


# __name__ tells that it's the root directory
app = Flask(__name__)
app.config.from_pyfile('config.py')
# db = SqliteDatabase(app.config['DATABASE_URI'])
cwd = os.getcwd()


@app.route('/')
def hello_world():
    return "<p>Hello World!</p>"


@app.route('/upload_image', methods=['POST'])
def upload_image():
    uploaded_file = request.files['image']
    target_path = os.path.join(
        app.config['UPLOAD_FOLDER'], uploaded_file.filename)
    if uploaded_file.filename != '':
        uploaded_file.save(target_path)
    return target_path
    

        