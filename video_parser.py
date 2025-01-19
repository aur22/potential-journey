import os
from flask import Flask, request, jsonify, make_response, send_from_directory
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
import yt_dlp
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
logger.addHandler(handler)

class Config:
    """应用配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'
    DEBUG = False
    PORT = int(os.environ.get('PORT', 5000))
    HOST = os.environ.get('HOST', '0.0.0.0')

def create_app():
    """创建Flask应用"""
    app = Flask(__name__, static_folder='public', static_url_path='')
    app.config.from_object(Config)
    
    # 配置CORS
    CORS(app)
    
    # 注册路由
    @app.route('/')
    def serve_index():
        return send_from_directory('public', 'index.html')

    @app.route('/parse', methods=['POST', 'OPTIONS'])
    def parse_video():
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers.update({
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })
            return response

        try:
            data = request.get_json()
            if not data or 'url' not in data:
                return jsonify({'error': '请提供视频URL'}), 400
                
            url = data['url']
            if not url:
                return jsonify({'error': '请提供视频URL'}), 400

            # 检查URL格式
            if not is_valid_url(url):
                return jsonify({'error': '不支持的视频平台或无效的URL'}), 400

            # 配置yt-dlp选项
            ydl_opts = {
                'format': 'best[ext=mp4]/best',  # 优先选择mp4格式
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'socket_timeout': 30,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # 获取视频信息
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        return jsonify({'error': '无法获取视频信息'}), 400

                    # 处理YouTube视频
                    if 'youtube.com' in url or 'youtu.be' in url:
                        if 'url' in info:
                            video_url = info['url']
                        else:
                            # 获取最佳格式
                            formats = info.get('formats', [])
                            if not formats:
                                return jsonify({'error': '无法获取视频格式'}), 400
                            
                            # 选择最佳的mp4格式
                            mp4_formats = [f for f in formats if f.get('ext') == 'mp4']
                            if mp4_formats:
                                best_format = max(mp4_formats, key=lambda f: f.get('filesize', 0))
                            else:
                                best_format = formats[-1]
                            
                            video_url = best_format.get('url')
                            if not video_url:
                                return jsonify({'error': '无法获取视频地址'}), 400
                    
                    # 处理其他平台视频
                    else:
                        video_url = info.get('url')
                        if not video_url:
                            formats = info.get('formats', [])
                            if formats:
                                best_format = formats[-1]
                                video_url = best_format.get('url')
                            
                            if not video_url:
                                return jsonify({'error': '无法获取视频地址'}), 400

                    # 返回成功响应
                    response = jsonify({
                        'url': video_url,
                        'title': info.get('title', ''),
                        'platform': 'youtube' if ('youtube.com' in url or 'youtu.be' in url) else 'other'
                    })
                    
                    response.headers.update({
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Cache-Control': 'no-cache'
                    })
                    return response
                    
            except yt_dlp.utils.DownloadError as e:
                logger.error(f"下载错误: {str(e)}")
                return jsonify({'error': '视频解析失败，请确认链接是否正确'}), 400
                
        except Exception as e:
            logger.error(f"解析错误: {str(e)}")
            return jsonify({'error': '服务器处理请求失败，请稍后重试'}), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': '请求的资源不存在'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': '服务器内部错误'}), 500

    return app

def is_valid_url(url):
    """检查URL是否为支持的视频平台"""
    patterns = [
        r'^https?:\/\/(www\.)?(youtube\.com|youtu\.be)',
        r'^https?:\/\/(www\.)?bilibili\.com',
        r'^https?:\/\/(www\.)?douyin\.com',
        r'^https?:\/\/(www\.)?kuaishou\.com'
    ]
    return any(re.match(pattern, url) for pattern in patterns)

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )