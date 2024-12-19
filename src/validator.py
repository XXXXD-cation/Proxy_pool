import requests
from typing import Dict, List
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

# 禁用 SSL 验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ProxyValidator')

class ProxyValidator:
    def __init__(self):
        self.test_urls = [
            'https://gitee.com/',
        ]
        self.timeout = 10
        self.max_workers = 50  # 最大线程数

    def validate_proxy(self, proxy: Dict) -> Dict:
        """验证单个代理"""
        start = time.time()
        proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
        proxies = {
            'http': proxy_url,
        }

        try:
            for test_url in self.test_urls:
                try:
                    response = requests.get(
                        test_url,
                        proxies=proxies,
                        timeout=self.timeout,
                        verify=False  # 忽略SSL证书验证
                    )
                    
                    if response.status_code == 200:
                        response_time = time.time() - start
                        proxy.update({
                            'response_time': response_time,
                            'status': 'valid',
                            'last_check': int(time.time()),
                            'checked_url': test_url,
                            'protocol': 'http',
                            'anonymity': 'high' if 'Via' not in response.headers else 'low'
                        })
                        logger.info(f"HTTP代理 {proxy['ip']}:{proxy['port']} 验证成功，响应时间: {response_time:.2f}秒")
                        return proxy
                except requests.Timeout:
                    logger.debug(f"测试URL {test_url} 超时")
                    continue
                except requests.RequestException as e:
                    logger.debug(f"测试URL {test_url} 失败: {str(e)}")
                    continue
            
            # 如果所有URL都失败
            proxy.update({
                'status': 'invalid',
                'last_check': int(time.time()),
                'protocol': 'http'
            })
            logger.warning(f"HTTP代理 {proxy['ip']}:{proxy['port']} 所有测试URL均失败")

        except Exception as e:
            proxy.update({
                'status': 'error',
                'last_check': int(time.time()),
                'protocol': 'http',
                'error_msg': str(e)
            })
            logger.error(f"HTTP代理 {proxy['ip']}:{proxy['port']} 验证出错: {str(e)}")

        return proxy

    def validate_proxies(self, proxies: List[Dict]) -> List[Dict]:
        """批量验证代理"""
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有验证任务
            future_to_proxy = {
                executor.submit(self.validate_proxy, proxy): proxy 
                for proxy in proxies
            }
            
            # 收集结果
            for future in as_completed(future_to_proxy):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    proxy = future_to_proxy[future]
                    logger.error(f"验证代理 {proxy['ip']}:{proxy['port']} 时发生异常: {str(e)}")
                    proxy.update({
                        'status': 'error',
                        'last_check': int(time.time()),
                        'error_msg': str(e)
                    })
                    results.append(proxy)

        # 统计验证结果
        status_count = {
            'valid': len([r for r in results if r['status'] == 'valid']),
            'invalid': len([r for r in results if r['status'] == 'invalid']),
            'timeout': len([r for r in results if r['status'] == 'timeout']),
            'error': len([r for r in results if r['status'] == 'error'])
        }
        
        logger.info(f"批量验证完成: 总数 {len(proxies)}, 有效数 {status_count['valid']}")
        logger.info(f"验证结果统计: {status_count}")
        
        return results
