"""Quick test script to verify the Flask app can make predictions"""
import requests
import sys
import os

def test_prediction(image_path):
    """Test prediction endpoint with an image file"""
    url = "http://127.0.0.1:5000/predict"
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Prediction successful!")
                print(f"   Sign: {result.get('sign_name')}")
                print(f"   Class: {result.get('predicted_class')}")
                print(f"   Confidence: {result.get('confidence'):.2%}")
                return True
            else:
                print(f"❌ Prediction failed: {result.get('error')}")
                return False
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask app. Is it running on http://127.0.0.1:5000?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    # Test with images from tests directory
    test_images = [
        'tests/speed-limit-sign-30-km-h.jpg',
        'tests/traffic-arrow-sign-only-left_23-2148445334.png'
    ]
    
    print("Testing predictions...\n")
    for img_path in test_images:
        if os.path.exists(img_path):
            print(f"Testing: {img_path}")
            test_prediction(img_path)
            print()
    
    print("Done!")
