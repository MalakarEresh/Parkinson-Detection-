from app import create_app, db
from app.models import User, Report

# The create_app function now handles loading the .env file via config.py
app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Report': Report}

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port)
