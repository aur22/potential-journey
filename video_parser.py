import os
from flask import Flask, request, jsonify, make_response, send_from_directory
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
import requests
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
logger.addHandler(handler)

# 解析接口列表
PARSE_APIS = [
    'https://jx.m3u8.tv/jiexi/?url=',  # 默认线路 - 稳定高清
    'https://www.8090g.cn/?url=',  # 备用线路1 - 无广告
    'https://jx.playerjy.com/?url=',  # 备用线路2 - 超清解析
    'https://jx.jsonplayer.com/player/?url=',  # 备用线路3 - 全网解析
    'https://jx.xmflv.com/?url=',  # 备用线路4 - 超清解析
    'https://api.jiexi.la/?url='  # 备用线路5 - 稳定高速
]

# 支持的视频平台
SUPPORTED_DOMAINS = [
    'v.qq.com',
    'iqiyi.com',
    'youku.com',
    'mgtv.com',
    'bilibili.com',
    'douyin.com',
    'kuaishou.com'
]

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

            # 尝试使用不同的解析接口
            for api in PARSE_APIS:
                try:
                    parse_url = api + url
                    logger.info(f"尝试使用接口: {api}")
                    
                    # 返回解析结果
                    response = jsonify({
                        'url': parse_url,
                        'title': '视频播放'
                    })
                    
                    response.headers.update({
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Cache-Control': 'no-cache'
                    })
                    return response
                    
                except Exception as e:
                    logger.error(f"解析接口 {api} 失败: {str(e)}")
                    continue
            
            return jsonify({'error': '视频解析失败，请稍后重试'}), 400
                
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
    return any(domain in url.lower() for domain in SUPPORTED_DOMAINS)

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )