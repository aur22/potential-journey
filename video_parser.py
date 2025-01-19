import os
from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
from functools import lru_cache
import requests
import logging
from logging.handlers import RotatingFileHandler
import time
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

# 禁用 urllib3 警告
requests.packages.urllib3.disable_warnings()

class Config:
    """应用配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'
    DEBUG = False
    PORT = int(os.environ.get('PORT', 5000))
    HOST = os.environ.get('HOST', '0.0.0.0')
    CORS_ORIGINS = '*'
    CACHE_CONTROL = 'no-cache, no-store, must-revalidate'

class VideoParser:
    """视频解析器类"""
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }

    PARSE_APIS = [
        "https://jx.jsonplayer.com/player/?url=",  # 默认线路
        "https://jx.xmflv.com/?url=",              # 备用线路1
        "https://jx.aidouer.net/?url=",            # 备用线路2
        "https://jx.playerjy.com/?url=",           # 备用线路3
        "https://jx.quankan.app/?url=",            # 备用线路4
        "https://jx.yparse.com/index.php?url=",    # 备用线路5
    ]

    SUPPORTED_DOMAINS = [
        'v.qq.com', 'iqiyi.com', 'youku.com', 'mgtv.com', 'bilibili.com',
        'sohu.com', 'le.com', 'pptv.com', '1905.com', 'fun.tv'
    ]

    def check_url(self, url):
        """检查URL是否为支持的视频网站"""
        try:
            return any(domain in url.lower() for domain in self.SUPPORTED_DOMAINS)
        except Exception as e:
            logger.error(f"URL检查失败: {str(e)}")
            return False

    def request_parse(self, api, url):
        """请求解析接口"""
        session = requests.Session()
        try:
            parse_url = api + url
            session.verify = False
            session.trust_env = False
            
            for attempt in range(3):
                try:
                    # 添加重试机制
                    for retry in range(2):
                        try:
                            response = session.get(
                                parse_url,
                                headers=self.HEADERS,
                                timeout=20,
                                allow_redirects=True
                            )
                            if response.status_code == 200:
                                logger.info(f"解析成功: {parse_url}")
                                return parse_url
                            elif response.status_code in [403, 404]:
                                logger.warning(f"接口访问受限或不存在: {parse_url}")
                                break
                            else:
                                logger.warning(f"请求返回状态码: {response.status_code}")
                                if retry < 1:
                                    time.sleep(1)
                                    continue
                        except requests.Timeout:
                            if retry < 1:
                                time.sleep(1)
                                continue
                            raise
                except requests.RequestException as e:
                    logger.warning(f"第{attempt + 1}次请求失败: {str(e)}")
                    if attempt < 2:
                        time.sleep(2)
                    continue
            
            logger.error(f"接口请求失败: {api}")
            return None
            
        except Exception as e:
            logger.error(f"解析请求异常: {str(e)}")
            return None
        finally:
            session.close()

    @lru_cache(maxsize=100)
    def parse_url(self, url, api_index=0):
        """解析视频URL"""
        try:
            if not self.check_url(url):
                return {'success': False, 'message': '不支持的视频网站，请输入正确的视频链接'}

            # 尝试所有接口
            for i in range(len(self.PARSE_APIS)):
                current_index = (api_index + i) % len(self.PARSE_APIS)
                result = self.request_parse(self.PARSE_APIS[current_index], url)
                if result:
                    return {
                        'success': True,
                        'data': {'url': result, 'type': 'iframe'}
                    }
                time.sleep(1)  # 接口之间添加延迟

            return {'success': False, 'message': '解析失败，请稍后重试'}
            
        except Exception as e:
            logger.error(f"URL解析失败: {str(e)}")
            return {'success': False, 'message': '解析过程发生错误，请稍后重试'}

def is_valid_url(url):
    # 支持的视频平台URL正则表达式
    patterns = [
        r'^https?:\/\/(www\.)?(youtube\.com|youtu\.be)',
        r'^https?:\/\/(www\.)?bilibili\.com',
        r'^https?:\/\/(www\.)?douyin\.com',
        r'^https?:\/\/(www\.)?kuaishou\.com'
    ]
    
    return any(re.match(pattern, url) for pattern in patterns)

def create_app():
    """创建Flask应用"""
    app = Flask(__name__, static_folder='public', static_url_path='')
    app.config.from_object(Config)
    
    # 配置CORS
    CORS(app)
    
    # 注册路由
    @app.route('/')
    def index():
        response = make_response(render_template('index.html'))
        response.headers.update({
            'Cache-Control': Config.CACHE_CONTROL,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
        return response

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
            if not data:
                return jsonify({'error': '无效的请求数据'}), 400
                
            url = data.get('url')
            if not url:
                return jsonify({'error': '请提供视频URL'}), 400
            
            if not is_valid_url(url):
                return jsonify({'error': '不支持的视频平台或无效的URL'}), 400

            ydl_opts = {
                'format': 'best',
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
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        return jsonify({'error': '无法获取视频信息'}), 400
                        
                    # 尝试获取不同格式的URL
                    video_url = info.get('url')
                    if not video_url:
                        formats = info.get('formats', [])
                        if formats:
                            # 选择最佳质量的格式
                            best_format = formats[-1]
                            video_url = best_format.get('url')
                    
                    if not video_url:
                        return jsonify({'error': '无法获取视频地址'}), 400
                        
                    response = jsonify({'url': video_url})
                    response.headers.update({
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
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

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )