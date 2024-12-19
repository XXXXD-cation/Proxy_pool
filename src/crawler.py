import json
import re
import requests
from lxml import etree
import time
from typing import List, Dict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ProxyCrawler')

class ProxyCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # 代理源配置，包含URL模板和页数
        self.proxy_sources = {
            'kuaidaili': {
                'url_template': 'https://www.kuaidaili.com/free/inha/{}/',
                'pages': 10
            },
            'ip3366': {
                'url_template': 'http://www.ip3366.net/free/?stype=1&page={}',
                'pages': 10
            },
            # '89ip': {
            #     'url_template': 'https://www.89ip.cn/index_{}.html',
            #     'pages': 10
            # },
            # 'ihuan': {
            #     'url_template': 'https://ip.ihuan.me/?page={}',
            #     'pages': 10
            # }
        }
        self.page_interval = 2  # 页面抓取间隔（秒）

    def crawl_all(self) -> List[Dict]:
        """抓取所有代理源"""
        proxies = []
        for source_name, source_config in self.proxy_sources.items():
            try:
                source_proxies = self.crawl_source(
                    source_name,
                    source_config['url_template'],
                    source_config['pages']
                )
                proxies.extend(source_proxies)
            except Exception as e:
                logger.error(f"爬取 {source_name} 代理失败: {str(e)}")
        return proxies

    def crawl_source(self, source_name: str, url_template: str, pages: int) -> List[Dict]:
        """抓取单个代理源的多个页面"""
        proxies = []

        for page in range(1, pages + 1):
            try:
                url = url_template.format(page)
                logger.info(f"爬取{source_name}第{page}页 : {url}")

                resp = requests.get(url, headers=self.headers, timeout=20)
                html = etree.HTML(resp.text)

                page_proxies = self.parse_page(source_name, resp.text, html)
                if page_proxies:
                    proxies.extend(page_proxies)
                    logger.info(f"从{source_name}代理的第{page}页，获取到 {len(page_proxies)} 条代理")

                if page < pages:
                    time.sleep(self.page_interval)

            except Exception as e:
                logger.error(f"爬取{source_name}代理第{page}页失败: {str(e)}")
                continue

        return proxies

    def parse_page(self, source_name: str, raw_html: str, html: etree._Element) -> List[Dict]:
        """解析单个页面"""
        proxies = []

        try:
            if source_name == 'kuaidaili':
                # 使用正则表达式提取 fpsList 的 JSON 数据
                script_content = extract_json_from_script(raw_html)
                if script_content:
                    proxy_data = json.loads(script_content)
                    for proxy in proxy_data:
                        proxies.append({
                            'ip': proxy['ip'].strip(),
                            'port': proxy['port'].strip(),
                            'source': source_name
                        })
                else:
                    # 如果没有找到JSON数据，使用xpath提取
                    ips = html.xpath('//td[@data-title="IP"]/text()')
                    ports = html.xpath('//td[@data-title="PORT"]/text()')
                    for ip, port in zip(ips, ports):
                        proxies.append({
                            'ip': ip.strip(),
                            'port': port.strip(),
                            'source': source_name
                        })

            elif source_name == 'ip3366':
                ips = html.xpath('//td[1]/text()')
                ports = html.xpath('//td[2]/text()')
                for ip, port in zip(ips, ports):
                    proxies.append({
                        'ip': ip.strip(),
                        'port': port.strip(),
                        'source': source_name
                    })

        except Exception as e:
            logger.error(f"解析{source_name}代理页失败: {str(e)}")

        return proxies


def extract_json_from_script(html_text):
    """从页面中的script中提取fpsList的JSON数据"""
    pattern = r'const fpsList = (\[.*?\]);'
    match = re.search(pattern, html_text)
    if match:
        return match.group(1)
    return None
