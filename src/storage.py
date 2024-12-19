import os
import redis
import json
from typing import Dict, List
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ProxyStorage')

class ProxyStorage:
    def __init__(self):
        self.redis = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            password='*********'
        )
        self.proxy_key = 'proxies'
        self.min_score = 0
        self.max_score = 100
        self.initial_score = 50

    def add_proxy(self, proxy: Dict):
        """添加代理"""
        proxy_str = json.dumps(proxy)
        self.redis.zadd(self.proxy_key, {proxy_str: self.initial_score})

    def get_proxy(self) -> Dict:
        """获取一个代理"""
        # 按分数从高到低获取
        proxies = self.redis.zrevrange(self.proxy_key, 0, 0)
        if proxies:
            return json.loads(proxies[0])
        return None

    def find_proxy(self, target_proxy: Dict) -> tuple:
        """根据ip和port查找代理及其分数"""
        all_proxies = self.redis.zrange(self.proxy_key, 0, -1, withscores=True)
        target_ip = target_proxy['ip']
        target_port = target_proxy['port']
        
        for proxy_str, score in all_proxies:
            try:
                proxy = json.loads(proxy_str)
                if proxy['ip'] == target_ip and proxy['port'] == target_port:
                    return proxy_str, score
            except json.JSONDecodeError:
                continue
        return None, None

    def decrease_score(self, proxy: Dict):
        """降低代理分数"""
        proxy_str, score = self.find_proxy(proxy)
        if proxy_str and score and score > self.min_score:
            self.redis.zincrby(self.proxy_key, -1, proxy_str)
            logger.info(f"Decreased score for {proxy['ip']}:{proxy['port']} to {score-1}")
        elif proxy_str:
            self.redis.zrem(self.proxy_key, proxy_str)
            logger.info(f"Removed proxy {proxy['ip']}:{proxy['port']} due to low score")

    def increase_score(self, proxy: Dict):
        """提升代理分数"""
        proxy_str, score = self.find_proxy(proxy)
        if proxy_str and score and score < self.max_score:
            self.redis.zincrby(self.proxy_key, 1, proxy_str)
            logger.info(f"Increased score for {proxy['ip']}:{proxy['port']} to {score+1}")

    def get_all_proxies(self) -> List[Dict]:
        """获取所有代理"""
        # 获取所有代理的字符串形式
        proxy_strings = self.redis.zrange(self.proxy_key, 0, -1)
        # 转换为字典列表
        proxies = []
        for proxy_str in proxy_strings:
            try:
                proxy = json.loads(proxy_str)
                proxies.append(proxy)
            except json.JSONDecodeError:
                continue
        return proxies

    def get_all_valid_proxies(self) -> List[Dict]:
        """获取所有可用代理，按分数从高到低排序"""
        # 获取所有代理的字符串形式，按分数从高到低排序
        proxy_strings = self.redis.zrevrange(self.proxy_key, 0, -1)
        proxies = []
        for proxy_str in proxy_strings:
            try:
                proxy = json.loads(proxy_str)
                score = self.redis.zscore(self.proxy_key, proxy_str)
                if score > self.min_score:  # 只返回分数大于小分数的代理
                    proxies.append(proxy)
            except json.JSONDecodeError:
                continue
        return proxies

    def remove_duplicates(self):
        """移除重复的代理"""
        # 获取所有代理
        all_proxies = self.redis.zrange(self.proxy_key, 0, -1, withscores=True)
        
        # 用于存储唯一代理
        unique_proxies = {}
        duplicates = []
        
        for proxy_str, score in all_proxies:
            try:
                proxy = json.loads(proxy_str)
                proxy_id = f"{proxy['ip']}:{proxy['port']}"
                
                if proxy_id in unique_proxies:
                    # 如果已存在，比较分数
                    if score > unique_proxies[proxy_id][1]:
                        # 如果新的分数更高，将旧的添加到待删除列表
                        duplicates.append(unique_proxies[proxy_id][0])
                        unique_proxies[proxy_id] = (proxy_str, score)
                    else:
                        # 如果旧的分数更高，将新的添加到待删除列表
                        duplicates.append(proxy_str)
                else:
                    unique_proxies[proxy_id] = (proxy_str, score)
                    
            except json.JSONDecodeError:
                # 如果解析失败，直接删除该代理
                duplicates.append(proxy_str)
        
        # 批量删除重复的代理
        if duplicates:
            self.redis.zrem(self.proxy_key, *duplicates)
            return len(duplicates)
        
        return 0