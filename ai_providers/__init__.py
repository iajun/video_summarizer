"""
AI Providers Module
提供各种AI服务的接口实现，支持API方式和浏览器方式
使用策略模式 + 工厂模式
"""

from .base import BaseAIProvider
from .factory import AIProviderFactory, get_provider
from .providers.api_provider import APIAIProvider
from .providers.browser_provider import BrowserAIProvider
from .providers.deepseek_provider import DeepSeekProvider
from .providers.chatgpt_provider import ChatGPTProvider
from .providers.yuanbao_provider import YuanBaoProvider

__all__ = [
    'BaseAIProvider',
    'AIProviderFactory',
    'get_provider',
    'APIAIProvider',
    'BrowserAIProvider',
    'DeepSeekProvider',
    'ChatGPTProvider',
    'YuanBaoProvider',
]

