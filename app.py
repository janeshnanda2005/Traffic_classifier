from flask import Flask, render_template, request, jsonify
import tensorflow as tf
import pandas as pd
import numpy as np
from PIL import Image
import os
import base64
from io import BytesIO
from datetime import datetime
import requests
import json

app = Flask(__name__)

# Load the trained model and class labels
model = tf.keras.models.load_model("traffic-sign.h5")
val = pd.read_csv("signname.csv")

# Upload folder config
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Firebase REST API configuration
FIREBASE_URL = "https://trafficclassifier-a476f-default-rtdb.asia-southeast1.firebasedatabase.app/"
API_KEY = "AIzaSyDCcQvjhTfFwHrcE2Gz4Uyya_E4SaMMXak"

def log_to_firebase(payload):
    url = f"{FIREBASE_URL}/predictions.json"
    params = {
        "auth": API_KEY
    }
    
    # Add headers for JSON content
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"Attempting to log to Firebase: {url}")
        print(f"Payload: {payload}")
        
        response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
        
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            print("✅ Successfully logged to Firebase")
            return True
        else:
            print(f"❌ Firebase error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error logging to Firebase: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error logging to Firebase: {e}")
        return False

def process_image(image_file):
    try:
        # Load and convert image
        image = Image.open(image_file).convert("RGB")
        image_resized = image.resize((32, 32))
        image_array = np.expand_dims(np.array(image_resized), axis=0)

        # Predict
        prediction = model.predict(image_array)
        predicted_class = np.argmax(prediction, axis=1)[0]
        confidence = float(np.max(prediction))

        # Get sign name - Fixed the logic here
        sign_name = "Unknown traffic sign"
        try:
            # Find the row where ClassId matches predicted_class
            matching_rows = val[val['ClassId'] == predicted_class]
            if not matching_rows.empty:
                sign_name = matching_rows['SignName'].iloc[0]
        except Exception as e:
            print(f"Error getting sign name: {e}")

        # Encode image to base64 for frontend display
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Create payload for Firebase - Fixed timestamp format
        firebase_payload = {
            'predicted_class': int(predicted_class),
            'sign_name': sign_name,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()[:19]  # Fixed: datetime.now().isoformat()
        }

        # Log to Firebase
        firebase_success = log_to_firebase(firebase_payload)
        
        return {
            'success': True,
            'sign_name': sign_name,
            'confidence': confidence,
            'image_data': img_base64,
            'firebase_logged': firebase_success  # Include Firebase status in response
        }

    except Exception as e:
        print(f"Error processing image: {e}")
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
        return jsonify({'success': False, 'error': 'Invalid file type. Use PNG, JPG, or JPEG.'})

# Test Firebase connection endpoint
@app.route('/test-firebase', methods=['GET'])
def test_firebase():
    test_payload = {
        'test': True,
        'message': 'Firebase connection test',
        'timestamp': datetime.now().isoformat()
    }
    
    success = log_to_firebase(test_payload)
    return jsonify({
        'firebase_test': success,
        'message': 'Check console for detailed logs'
    })

if __name__ == '__main__':
    print("🚀 Starting Flask app...")
    print(f"Firebase URL: {FIREBASE_URL}")
    print("Visit http://localhost:5000/test-firebase to test Firebase connection")
    app.run(debug=True, port=5000)