import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from peewee import *
from utils import *
import json
import uuid


# __name__ tells that it's the root directory
app = Flask(__name__)
app.config.from_pyfile('config.py')
db = SqliteDatabase(app.config['DATABASE_URI'])
cwd = os.getcwd()


@app.before_request
def before_request():
    db.connect()

@app.after_request
def after_request(response):
    db.close()
    return response


class BaseModel(Model):
    class Meta:
        database = db

class Medicine(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    description = TextField()
    composition = CharField()
    dosage = CharField()
    how_to_use = CharField()
    contraindication = TextField()
    side_effects = TextField()
    warning = TextField()


def create_tables():
    with db:
        db.create_tables([Medicine])

def insert_medicine_data():
    id = 1
    with open('drugs.json', 'r') as json_file:
        data = json.load(json_file)
        data = data['data']

    with db.atomic():
        for dict in data:
            Medicine.create(id=id, **dict)
            id += 1



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def hello_world():
    return "<p>Hello World!</p>"


@app.route('/medicine', methods=['GET', 'POST'])
def get_medicine():
    medicines = Medicine.select().limit(20)
    data = []
    for medicine in medicines:
        new_data = {
            'name': medicine.name,
            'description': medicine.description,
            'composition': medicine.composition,
            'dosage': medicine.dosage,
            'how_to_use': medicine.how_to_use,
            'contraindication': medicine.contraindication,
            'side_effects': medicine.side_effects,
            'warning': medicine.warning
        }
        data.append(new_data)
    return jsonify({'status': 200, 'data': data})


@app.route('/medicine/<name>', methods=['GET'])
def get_medicine_by_name(name):
    try:
        medicines = Medicine.select().where(Medicine.name.startswith(name))
    except:
        return jsonify({
            'status': 200,
            'data': []
        })

    data = []
    for medicine in medicines:
        new_data = {
            'name': medicine.name,
            'description': medicine.description,
            'composition': medicine.composition,
            'dosage': medicine.dosage,
            'how_to_use': medicine.how_to_use,
            'contraindication': medicine.contraindication,
            'side_effects': medicine.side_effects,
            'warning': medicine.warning
        }
        data.append(new_data)
    return jsonify({'status': 200, 'data': data})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    uploaded_file = request.files['image']
    # filename = secure_filename(uploaded_file.filename)
    ext = os.path.splitext(uploaded_file.filename)[1]
    filename = str(uuid.uuid4().hex) + ext
    target_path = os.path.join(
        app.config['UPLOAD_FOLDER'], filename)
    
    if not allowed_file(filename):
        return {'status': 400, 'message': f'{filename} not allowed'}
    
    if uploaded_file.filename != '':
        try:
            uploaded_file.save(target_path)
        except:
            return {'status': 400, 'message': 'Failed to save the image'}
    return target_path


if __name__ == '__main__':
    app.run(debug=True)