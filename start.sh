# Render Start Command
# This tells Render how to start your application in production

# Use Gunicorn as the WSGI server for production
gunicorn --bind 0.0.0.0:$PORT app:app
