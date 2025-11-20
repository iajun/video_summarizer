"""
API方式AI提供者基类
用于通过API调用AI服务（如DeepSeek API）
"""

from abc import abstractmethod
from typing import Optional
from ..base import BaseAIProvider


class APIAIProvider(BaseAIProvider):
    """API方式AI提供者基类"""
    
    def __init__(self, name: str, api_key: Optional[str] = None, config: Optional[dict] = None):
        """
        初始化API提供者
        
        Args:
            name: 提供者名称
            api_key: API密钥
            config: 额外配置（如model、temperature等）
        """
        super().__init__(name, config)
        self.api_key = api_key or (config.get('api_key') if config else None)
    
    def get_provider_type(self) -> str:
        return 'api'
    
    def is_configured(self) -> bool:
        """检查API密钥是否已配置"""
        return bool(self.api_key)
    
    @abstractmethod
    async def summarize(self, text: str, prompt_template: Optional[str] = None) -> Optional[str]:
        """
        使用API进行总结
        
        Args:
            text: 要总结的文本
            prompt_template: 提示词模板
            
        Returns:
            总结结果
        """
        pass
    
    def _build_prompt(self, text: str, prompt_template: Optional[str] = None) -> str:
        """
        构建最终的提示词
        
        Args:
            text: 要总结的文本
            prompt_template: 提示词模板（包含{text}占位符）
            
        Returns:
            完整的提示词
        """
        if prompt_template:
            if '{text}' in prompt_template:
                return prompt_template.format(text=text)
            else:
                return f"{prompt_template}\n\n{text}"
        else:
            return f"请总结以下内容：\n\n{text}"

