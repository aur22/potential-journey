from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import re
import os

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# 解析接口列表
PARSE_APIS = [
    "https://jx.jsonplayer.com/player/?url=",  # 默认线路
    "https://jx.xmflv.com/?url=",              # 备用线路1
    "https://jx.aidouer.net/?url=",            # 备用线路2
    "https://jx.playerjy.com/?url=",           # 备用线路3
    "https://jx.quankan.app/?url=",            # 备用线路4
]

# 支持的视频平台
SUPPORTED_DOMAINS = [
    'v.qq.com', 'iqiyi.com', 'youku.com', 'mgtv.com', 'bilibili.com',
    'sohu.com', 'le.com', 'pptv.com', '1905.com', 'fun.tv', 'douyin.com'
]

def is_valid_url(url):
    """检查URL是否为支持的视频网站"""
    try:
        return any(domain in url.lower() for domain in SUPPORTED_DOMAINS)
    except:
        return False

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

        # 尝试所有解析接口
        for api in PARSE_APIS:
            try:
                parse_url = api + url
                response = jsonify({
                    'url': parse_url,
                    'title': '视频播放',
                    'platform': 'other'
                })
                response.headers.update({
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Cache-Control': 'no-cache'
                })
                return response
            except:
                continue

        return jsonify({'error': '解析失败，请稍后重试'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 