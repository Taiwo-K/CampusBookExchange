"""
Entry point.

Development:   flask --app wsgi run --debug
Production:    gunicorn wsgi:app
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
