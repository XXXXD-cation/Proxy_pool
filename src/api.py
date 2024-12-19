from flask import Flask, jsonify
from storage import ProxyStorage
import threading

app = Flask(__name__)
storage = ProxyStorage()


# 添加轮询计数器
class ProxyCounter:
    def __init__(self):
        self.index = 0
        self.lock = threading.Lock()

    def get_next_index(self, max_index):
        with self.lock:
            current = self.index
            self.index = (self.index + 1) % max_index if max_index > 0 else 0
            return current


counter = ProxyCounter()


@app.route('/get_proxy')
def get_proxy():
    """获取代理接口 - 轮询方式"""
    proxies = storage.get_all_valid_proxies()
    if not proxies:
        return jsonify({'error': 'no proxy available'})

    # 获取下一个代理的索引
    index = counter.get_next_index(len(proxies))
    proxy = proxies[index]

    # 返回代理信息和当前代理池大小
    return jsonify({
        'proxy': proxy,
        'total_proxies': len(proxies),
        'current_index': index
    })


@app.route('/get_all_proxies')
def get_all_proxies():
    """获取所有可用代理"""
    proxies = storage.get_all_valid_proxies()
    return jsonify({
        'proxies': proxies,
        'total': len(proxies)
    })


@app.route('/feedback/<ip>/<port>/<status>')
def feedback(ip, port, status):
    """代理反馈接口"""
    proxy = {'ip': ip, 'port': port}
    try:
        if status == 'valid':
            storage.increase_score(proxy)
            return jsonify({
                'message': '已收到反馈',
                'action': '提高目标代理分数',
                'proxy': f"{ip}:{port}"
            })
        else:
            storage.decrease_score(proxy)
            return jsonify({
                'message': '已收到反馈',
                'action': '降低目标代理分数',
                'proxy': f"{ip}:{port}"
            })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'proxy': f"{ip}:{port}",
            'status': status
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
