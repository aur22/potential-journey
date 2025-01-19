from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from video_parser import VideoParser
import os

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

parser = VideoParser()

@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

@app.route('/parse', methods=['POST', 'OPTIONS'])
def parse():
    if request.method == 'OPTIONS':
        return '', 204
    
    url = request.json.get('url')
    if not url:
        return jsonify({'error': '请输入视频链接'}), 400
        
    try:
        video_url = parser.parse_url(url)
        return jsonify({'url': video_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 