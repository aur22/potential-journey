from flask import Flask, render_template, request, jsonify
from functools import lru_cache
import requests
requests.packages.urllib3.disable_warnings()

app = Flask(__name__)

class VideoParser:
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    }

    PARSE_APIS = [
        "https://www.8090g.cn/?url=",             # 默认线路 - 无广告高速
        "https://jx.jsonplayer.com/player/?url=",  # 备用线路1 - 稳定无广告
        "https://jx.xmflv.com/?url=",             # 备用线路2 - 超清无广告
    ]

    SUPPORTED_DOMAINS = [
        'v.qq.com', 'iqiyi.com', 'youku.com', 'mgtv.com', 'bilibili.com',
        'sohu.com', 'le.com', 'pptv.com', '1905.com', 'fun.tv'
    ]

    def check_url(self, url):
        """检查URL是否为支持的视频网站"""
        return any(domain in url.lower() for domain in self.SUPPORTED_DOMAINS)

    def request_parse(self, api, url):
        """请求解析接口"""
        try:
            parse_url = api + url
            session = requests.Session()
            session.verify = False
            session.trust_env = False
            for _ in range(2):
                try:
                    response = session.get(
                        parse_url,
                        headers=self.HEADERS,
                        timeout=5,
                        allow_redirects=True
                    )
                    if response.status_code == 200:
                        return parse_url
                except requests.RequestException:
                    continue
            return None
        except Exception:
            return None
        finally:
            session.close()

    @lru_cache(maxsize=100)
    def parse_url(self, url, api_index=0):
        """解析视频URL"""
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

        return {'success': False, 'message': '解析失败，请尝试其他线路'}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def parse():
    url = request.form.get('url', '').strip()
    api_index = int(request.form.get('api_index', 0))

    if not url:
        return jsonify({'success': False, 'message': '请输入视频URL'})

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parser = VideoParser()
    if api_index >= len(parser.PARSE_APIS):
        return jsonify({'success': False, 'message': '无效的接口选择'})

    return jsonify(parser.parse_url(url, api_index))

if __name__ == '__main__':
    app.run(debug=True, port=5000)