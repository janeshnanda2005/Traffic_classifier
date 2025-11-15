"""
Configuration file for Traffic Sign Classifier
Supports environment variables for flexible deployment
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Flask Configuration
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
PORT = int(os.getenv('PORT', 5000))
HOST = os.getenv('HOST', '0.0.0.0')

# Model Configuration
MODEL_PATH = os.getenv('MODEL_PATH', str(BASE_DIR / 'traffic-sign.h5'))
SIGNNAME_CSV = os.getenv('SIGNNAME_CSV', str(BASE_DIR / 'signname.csv'))

# Upload Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', str(BASE_DIR / 'static' / 'uploads'))
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Image Processing
IMAGE_SIZE = (32, 32)  # Model input size

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.getenv('LOG_FILE', str(BASE_DIR / 'logs' / 'app.log'))

# CORS Configuration (for API access from different domains)
CORS_ENABLED = os.getenv('CORS_ENABLED', 'False').lower() == 'true'
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

# Model Loading Configuration
EAGER_LOAD_MODEL = os.getenv('EAGER_LOAD_MODEL', 'False').lower() == 'true'
