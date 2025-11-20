"""
AI Provider 抽象基类
定义所有AI服务提供者的统一接口
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseAIProvider(ABC):
    """AI服务提供者基类"""
    
    def __init__(self, name: str, config: Optional[dict] = None):
        """
        初始化AI提供者
        
        Args:
            name: 提供者名称
            config: 配置字典，包含api_key、cookies等
        """
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    async def summarize(self, text: str, prompt_template: Optional[str] = None) -> Optional[str]:
        """
        总结文本内容
        
        Args:
            text: 要总结的文本
            prompt_template: 提示词模板（可选）
            
        Returns:
            总结结果，失败返回None
        """
        pass
    
    @abstractmethod
    def get_provider_type(self) -> str:
        """
        获取提供者类型
        
        Returns:
            'api' 或 'browser'
        """
        pass
    
    def get_name(self) -> str:
        """获取提供者名称"""
        return self.name
    
    def is_configured(self) -> bool:
        """
        检查提供者是否已正确配置
        
        Returns:
            是否已配置
        """
        return True

