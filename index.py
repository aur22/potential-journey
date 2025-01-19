from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import re
import os

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# 支持的视频平台
SUPPORTED_PLATFORMS = [
    r'^https?:\/\/(www\.)?(youtube\.com|youtu\.be)',
    r'^https?:\/\/(www\.)?bilibili\.com',
    r'^https?:\/\/(www\.)?douyin\.com',
    r'^https?:\/\/(www\.)?kuaishou\.com'
]

def is_valid_url(url):
    """检查URL是否为支持的视频平台"""
    return any(re.match(pattern, url) for pattern in SUPPORTED_PLATFORMS)

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/parse', methods=['POST', 'OPTIONS'])
def parse():
    # 处理 OPTIONS 请求
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
        return response

    try:
        # 获取请求数据
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': '请提供视频URL'}), 400

        url = data['url'].strip()
        if not url:
            return jsonify({'error': '请提供视频URL'}), 400

        # 验证URL
        if not is_valid_url(url):
            return jsonify({'error': '不支持的视频平台或无效的URL'}), 400

        # yt-dlp配置
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # 优先mp4格式
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }

        # 解析视频
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return jsonify({'error': '无法获取视频信息'}), 400

                # 获取视频URL
                video_url = info.get('url')
                if not video_url:
                    formats = info.get('formats', [])
                    if formats:
                        # 选择最佳格式
                        best_format = formats[-1]
                        video_url = best_format.get('url')

                if not video_url:
                    return jsonify({'error': '无法获取视频地址'}), 400

                # 返回结果
                response = jsonify({
                    'url': video_url,
                    'title': info.get('title', '未知标题'),
                    'platform': 'youtube' if ('youtube.com' in url or 'youtu.be' in url) else 'other'
                })

                # 设置响应头
                response.headers.update({
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Cache-Control': 'no-cache'
                })
                return response

            except yt_dlp.utils.DownloadError as e:
                return jsonify({'error': '视频解析失败，请确认链接是否正确'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 