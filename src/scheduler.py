import time
import asyncio
from crawler import ProxyCrawler
from validator import ProxyValidator
from storage import ProxyStorage
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ProxyScheduler')

class ProxyScheduler:
    def __init__(self):
        self.crawler = ProxyCrawler()
        self.validator = ProxyValidator()
        self.storage = ProxyStorage()

    async def schedule_crawl(self):
        """定时抓取任务"""
        while True:
            logger.info("开始获取代理...")
            proxies = self.crawler.crawl_all()
            valid_proxies = self.validator.validate_proxies(proxies)

            for proxy in valid_proxies:
                if proxy['status'] == 'valid':
                    self.storage.add_proxy(proxy)
                
            # 在每次抓取完成后进行去重
            removed = self.storage.remove_duplicates()
            logger.info(f"移除了 {removed} 个重复代理")

            await asyncio.sleep(3600)  # 每小时抓取一次

    async def schedule_validate(self):
        """定时验证任务"""
        while True:
            logger.info("开始验证代理可用性...")
            proxies = self.storage.get_all_proxies()
            validation_results = self.validator.validate_proxies(proxies)

            # 更新存储
            for proxy in validation_results:
                if proxy['status'] == 'invalid':
                    self.storage.decrease_score(proxy)
                elif proxy['status'] == 'valid':
                    self.storage.increase_score(proxy)

            await asyncio.sleep(300)  # 每5分钟验证一次
            
    async def schedule_cleanup(self):
        """定期清理任务"""
        while True:
            logger.info("开始代理去重...")
            removed = self.storage.remove_duplicates()
            logger.info(f"移除了 {removed} 个重复代理")
            await asyncio.sleep(1800)  # 每30分钟清理一次

    async def run(self):
        """运行调度器"""
        tasks = [
            self.schedule_crawl(),
            self.schedule_validate(),
            self.schedule_cleanup()
        ]
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    scheduler = ProxyScheduler()
    asyncio.run(scheduler.run())
