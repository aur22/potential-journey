from flask import Flask, send_from_directory
from video_parser import create_app

app = create_app()

@app.route('/')
def serve_index():
    return send_from_directory('templates', 'index.html')

if __name__ == "__main__":
    app.run() 