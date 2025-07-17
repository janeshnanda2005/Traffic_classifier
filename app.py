from flask import Flask, render_template, request, jsonify
import tensorflow as tf
import pandas as pd
import numpy as np
from PIL import Image
import os
import base64
from io import BytesIO

app = Flask(__name__)

# Load the model and CSV data
model = tf.keras.models.load_model("traffic-sign.h5")
val = pd.read_csv("signname.csv")

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def process_image(image_file):
    """Process uploaded image and make prediction"""
    try:
        # Open and convert image
        image = Image.open(image_file)
        image = image.convert("RGB")
        
        # Resize for model input
        image_resized = image.resize((32, 32))
        imagearr = np.array(image_resized)
        imagearr = np.expand_dims(imagearr, axis=0)
        
        # Make prediction
        prediction = model.predict(imagearr)
        pre_class = np.argmax(prediction, axis=1)
        
        # Get sign name
        if pre_class[0] < len(val) and pre_class[0] == val['ClassId'][pre_class[0]]:
            sign_name = val['SignName'][val['ClassId'][pre_class[0]]]
        else:
            sign_name = "Unknown traffic sign"
        
        # Convert image to base64 for display
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            'success': True,
            'sign_name': sign_name,
            'confidence': float(np.max(prediction)),
            'image_data': img_str
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        result = process_image(file)
        return jsonify(result)
    else:
        return jsonify({'success': False, 'error': 'Invalid file type. Please upload PNG, JPG, or JPEG files.'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)