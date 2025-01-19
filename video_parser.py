import os
from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
from functools import lru_cache
import requests
import logging
from logging.handlers import RotatingFileHandler
import time

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
    CORS_ORIGINS = '*'  # 允许所有来源
    CACHE_CONTROL = 'no-cache, no-store, must-revalidate'

class VideoParser:
    """视频解析器类"""
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'iframe',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site'
    }

    PARSE_APIS = [
        "https://jx.jsonplayer.com/player/?url=",  # 默认线路 - 稳定无广告
        "https://jx.xmflv.com/?url=",              # 备用线路1 - 超清无广告
        "https://jx.xyflv.cc/?url=",               # 备用线路2 - 稳定高速
        "https://jx.m3u8.tv/jiexi/?url=",         # 备用线路3 - 稳定高清
        "https://www.ckmov.vip/api.php?url=",     # 备用线路4 - 全网解析
        "https://www.pangujiexi.cc/jiexi.php?url=" # 备用线路5 - 备用高清
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
            
            for attempt in range(3):  # 增加重试次数
                try:
                    response = session.get(
                        parse_url,
                        headers=self.HEADERS,
                        timeout=15,  # 增加超时时间
                        allow_redirects=True
                    )
                    if response.status_code == 200:
                        logger.info(f"解析成功: {parse_url}")
                        return parse_url
                    elif response.status_code in [403, 404]:
                        logger.warning(f"接口访问受限或不存在: {parse_url}")
                        break  # 直接尝试下一个接口
                    else:
                        logger.warning(f"请求返回状态码: {response.status_code}")
                except requests.RequestException as e:
                    logger.warning(f"第{attempt + 1}次请求失败: {str(e)}")
                    if attempt < 2:
                        time.sleep(2)  # 增加重试等待时间
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

            # 尝试使用指定接口
            result = self.request_parse(self.PARSE_APIS[api_index], url)
            if result:
                return {
                    'success': True,
                    'data': {'url': result, 'type': 'iframe'}
                }

            # 尝试其他接口
            for i, api in enumerate(self.PARSE_APIS):
                if i != api_index:
                    result = self.request_parse(api, url)
                    if result:
                        return {
                            'success': True,
                            'data': {'url': result, 'type': 'iframe'}
                        }

            return {'success': False, 'message': '解析失败，请稍后重试'}
            
        except Exception as e:
            logger.error(f"URL解析失败: {str(e)}")
            return {'success': False, 'message': '解析过程发生错误，请稍后重试'}

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 配置CORS
    CORS(app, resources={
        r"/*": {
            "origins": ["*"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": True,
            "max_age": 600
        }
    })
    
    # 注册路由
    @app.route('/')
    def index():
        response = make_response(render_template('index.html'))
        response.headers.update({
            'Cache-Control': Config.CACHE_CONTROL,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
        })
        return response

    @app.route('/parse', methods=['POST', 'OPTIONS'])
    def parse():
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers.update({
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
            })
            return response

        try:
            url = request.form.get('url', '').strip()
            api_index = int(request.form.get('api_index', 0))

            if not url:
                return jsonify({'success': False, 'message': '请输入视频URL'})

            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            parser = VideoParser()
            if api_index >= len(parser.PARSE_APIS):
                return jsonify({'success': False, 'message': '无效的接口选择'})

            result = parser.parse_url(url, api_index)
            response = make_response(jsonify(result))
            response.headers.update({
                'Cache-Control': Config.CACHE_CONTROL,
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
            })
            return response
            
        except Exception as e:
            logger.error(f"解析请求处理失败: {str(e)}")
            return jsonify({'success': False, 'message': '服务器处理请求失败，请稍后重试'})

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'success': False, 'message': '请求的资源不存在'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )