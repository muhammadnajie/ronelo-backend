import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from peewee import *
import json
import uuid 
import numpy as np
import cv2
from imutils.object_detection import non_max_suppression
import pytesseract
import matplotlib.pyplot as plt



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


def find_roi(image_loc):

    #Creating argument dictionary for the default arguments needed in the code. 
    args = {"image":image_loc, "east": "frozen_east_text_detection.pb", "min_confidence":0.9, "width":320, "height":320}

    image = cv2.imread(args['image'])

    #Saving a original image and shape
    orig = image.copy()
    (origH, origW) = image.shape[:2]

    # set the new height and width to default 320 by using args #dictionary.  
    (newW, newH) = (args["width"], args["height"])

    #Calculate the ratio between original and new image for both height and weight. 
    #This ratio will be used to translate bounding box location on the original image. 
    rW = origW / float(newW)
    rH = origH / float(newH)

    # resize the original image to new dimensions
    image = cv2.resize(image, (newW, newH))
    (H, W) = image.shape[:2]

    # construct a blob from the image to forward pass it to EAST model
    blob = cv2.dnn.blobFromImage(image, 1.0, (W, H),
	    (123.68, 116.78, 103.94), swapRB=True, crop=False)

    # load the pre-trained EAST model for text detection 
    net = cv2.dnn.readNet(args["east"])

    # The following two layer need to pulled from EAST model for achieving this. 
    layerNames = [
        "feature_fusion/Conv_7/Sigmoid",
        "feature_fusion/concat_3"]
    
    #Forward pass the blob from the image to get the desired output layers
    net.setInput(blob)
    (scores, geometry) = net.forward(layerNames)

    (numR, numC) = scores.shape[2:4]
    boxes = []
    confidence_val = []

    # loop over rows
    for y in range(0, numR):
        scoresData = scores[0, 0, y]
        x0 = geometry[0, 0, y]
        x1 = geometry[0, 1, y]
        x2 = geometry[0, 2, y]
        x3 = geometry[0, 3, y]
        anglesData = geometry[0, 4, y]

        # loop over rows
        for y in range(0, numR):
            scoresData = scores[0, 0, y]
            x0 = geometry[0, 0, y]
            x1 = geometry[0, 1, y]
            x2 = geometry[0, 2, y]
            x3 = geometry[0, 3, y]
            anglesData = geometry[0, 4, y]

            # loop over the number of columns 
            for i in range(0, numC):
                if scoresData[i] < args["min_confidence"]:
                    continue

                (offX, offY) = (i * 4.0, y * 4.0)

                # extracting the rotation angle for the prediction and computing the sine and cosine
                angle = anglesData[i]
                cos = np.cos(angle)
                sin = np.sin(angle)

                # using the geo volume to get the dimensions of the bounding box
                h = x0[i] + x2[i]
                w = x1[i] + x3[i]

                # compute start and end for the text pred bbox
                endX = int(offX + (cos * x1[i]) + (sin * x2[i]))
                endY = int(offY - (sin * x1[i]) + (cos * x2[i]))
                startX = int(endX - w)
                startY = int(endY - h)

                boxes.append((startX, startY, endX, endY))
                confidence_val.append(scoresData[i])

    # return bounding boxes and associated confidence_val
    return (boxes, confidence_val, rW, rH, orig)


@app.route('/predict', methods=['POST'])
def predict():
    #upload image
    uploaded_file = request.files['image']
    # filename = secure_filename(uploaded_file.filename)

    if not allowed_file(uploaded_file.filename):
        return {'status': 400, 'message': f'{uploaded_file.filename} not allowed'}

    ext = os.path.splitext(uploaded_file.filename)[1]
    filename = str(uuid.uuid4().hex) + ext
    target_path = os.path.join(
        app.config['UPLOAD_FOLDER'], filename)
    
    if uploaded_file.filename != '':
        try:
            uploaded_file.save(target_path)
        except:
            return {'status': 400, 'message': 'Failed to save the image' + target_path}
    # return jsonify({'data': target_path, 'status': 200})

    #find Region of Interest
    (boxes, confidence_val, rW, rH, orig) = find_roi(target_path)
    boxes = non_max_suppression(np.array(boxes), probs=confidence_val)

    ##Text Detection and Recognition 

    # initialize the list of results
    results = []
    
    for (startX, startY, endX, endY) in boxes:
	# scale the coordinates based on the respective ratios in order to reflect bounding box on the original image
        startX = int(startX * rW)
        startY = int(startY * rH)
        endX = int(endX * rW)
        endY = int(endY * rH)

        #extract the region of interest
        r = orig[startY:endY, startX:endX]

        #configuration setting to convert image to string.  
        configuration = ("-l eng --oem 1 --psm 8")
        ##This will recognize the text from the image of bounding box
        text = pytesseract.image_to_string(r, config=configuration)

        # append bbox coordinate and associated text to the list of results 
        results.append(((startX, startY, endX, endY), text))

    medicines = []
    for _, name in results:
        with app.app_context():
            medicine = get_medicine_by_name(name[:-2])
        
        medicine = json.loads(medicine.data)
        if medicine['data']:
            medicines.append(medicine['data'])
        
    return jsonify({
        'status': 200,
        'data' : medicines
    })
    

if __name__ == '__main__':
    app.run()