import requests

def get_proxy(api_url: str):
    """从代理池 API 获取代理"""
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()  # 确保响应状态码为 2xx
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching proxy: {e}")
        return None

def report_proxy_status(proxy_data, status: str):
    """报告代理的状态"""
    proxy_ip = proxy_data["proxy"]["ip"]
    proxy_port = proxy_data["proxy"]["port"]
    feedback_url = f'http://localhost:5000/feedback/{proxy_ip}/{proxy_port}/{status}'
    try:
        response = requests.get(feedback_url)
        response.raise_for_status()  # 确保反馈 API 请求成功
        return response.json()
    except requests.RequestException as e:
        print(f"Error reporting proxy status: {e}")
        return None

def test_proxy(proxy: str, dest_url: str):
    """测试代理是否有效"""
    try:
        response = requests.get(dest_url, proxies={'http': proxy}, timeout=10)
        response.raise_for_status()  # 确保响应状态码为 2xx
        return True
    except requests.RequestException as e:
        print(f"Error with proxy {proxy}: {e}")
        return False

def main():
    api_url = 'http://localhost:5000/get_proxy'
    dest_url = 'https://gitee.com'
    username = 'admin'
    password = 'admin123'

    # 获取代理
    proxy_data = get_proxy(api_url)
    if not proxy_data:
        return  # 无法获取代理，直接返回

    proxy = f'http://{proxy_data["proxy"]["ip"]}:{proxy_data["proxy"]["port"]}'
    print(f"Testing proxy: {proxy}")

    # 测试代理有效性
    if test_proxy(proxy, dest_url):
        print("Proxy is valid.")
        report_proxy_status(proxy_data, status='valid')
    else:
        print("Proxy is invalid.")
        report_proxy_status(proxy_data, status='invalid')

if __name__ == "__main__":
    main()
