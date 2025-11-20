"""
AI Provider 工厂类
用于创建和管理AI服务提供者实例
"""

from typing import Optional, Dict, Any
from .base import BaseAIProvider
from .providers.deepseek_provider import DeepSeekProvider
from .providers.chatgpt_provider import ChatGPTProvider
from .providers.yuanbao_provider import YuanBaoProvider


class AIProviderFactory:
    """AI提供者工厂类"""
    
    # 注册的提供者类型
    _providers: Dict[str, type] = {
        'deepseek': DeepSeekProvider,
        'chatgpt': ChatGPTProvider,
        'yuanbao': YuanBaoProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        注册新的提供者类型
        
        Args:
            name: 提供者名称
            provider_class: 提供者类（必须继承自BaseAIProvider）
        """
        if not issubclass(provider_class, BaseAIProvider):
            raise TypeError(f"Provider class must inherit from BaseAIProvider")
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def create_provider(
        cls,
        name: str,
        provider_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseAIProvider]:
        """
        创建AI提供者实例
        
        Args:
            name: 提供者名称（如 'deepseek', 'chatgpt', 'yuanbao'）
            provider_type: 提供者类型（可选，用于验证）
            config: 配置字典，包含：
                - api_key: API密钥（用于API方式）
                - cookies: Cookies（用于浏览器方式）
                - model: 模型名称
                - max_tokens: 最大token数
                - temperature: 温度
                - system_prompt: 系统提示词
                
        Returns:
            AI提供者实例，如果名称不存在则返回None
        """
        name_lower = name.lower()
        
        if name_lower not in cls._providers:
            print(f"未知的AI提供者: {name}")
            return None
        
        provider_class = cls._providers[name_lower]
        config = config or {}
        
        try:
            # 根据提供者类型创建实例
            if name_lower == 'deepseek':
                api_key = config.get('api_key')
                return provider_class(api_key=api_key, config=config)
            elif name_lower in ['chatgpt', 'yuanbao']:
                cookies = config.get('cookies')
                return provider_class(cookies=cookies, config=config)
            else:
                # 通用创建方式
                return provider_class(config=config)
        except Exception as e:
            print(f"创建AI提供者失败: {name}, 错误: {e}")
            return None
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """
        列出所有已注册的提供者名称
        
        Returns:
            提供者名称列表
        """
        return list(cls._providers.keys())
    
    @classmethod
    def is_provider_available(cls, name: str) -> bool:
        """
        检查提供者是否可用
        
        Args:
            name: 提供者名称
            
        Returns:
            是否可用
        """
        return name.lower() in cls._providers


def get_provider(
    name: str,
    config: Optional[Dict[str, Any]] = None
) -> Optional[BaseAIProvider]:
    """
    便捷函数：获取AI提供者实例
    
    Args:
        name: 提供者名称
        config: 配置字典
        
    Returns:
        AI提供者实例
    """
    return AIProviderFactory.create_provider(name, config=config)

