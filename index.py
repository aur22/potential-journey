from flask import Flask, send_file
from video_parser import create_app
import os

app = create_app()

@app.route('/')
def serve_index():
    return send_file('public/index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 