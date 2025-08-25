# wsgi.py
import os

# Use non-GUI backend for Matplotlib
import matplotlib
matplotlib.use("Agg")

# Import Flask app factory
from app import create_app

# Create Flask app
app = create_app()

# Optional: Pre-import heavy ML libraries to catch issues early
try:
    import tensorflow as tf
except Exception as e:
    print(f"TensorFlow import warning: {e}")

# Gunicorn will look for 'app' by default
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
