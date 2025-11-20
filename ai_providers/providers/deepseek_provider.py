"""
DeepSeek API 提供者
使用DeepSeek API进行文本总结
"""

from typing import Optional
from openai import OpenAI

from .api_provider import APIAIProvider


class DeepSeekProvider(APIAIProvider):
    """DeepSeek API提供者"""
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[dict] = None):
        """
        初始化DeepSeek提供者
        
        Args:
            api_key: DeepSeek API密钥
            config: 额外配置，包含：
                - model: 模型名称（默认: "deepseek-chat"）
                - max_tokens: 最大token数（默认: 2000）
                - temperature: 温度（默认: 0.7）
                - system_prompt: 系统提示词（可选）
        """
        super().__init__("DeepSeek", api_key, config)
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
    
    async def summarize(self, text: str, prompt_template: Optional[str] = None) -> Optional[str]:
        """
        使用DeepSeek API进行总结
        
        Args:
            text: 要总结的文本
            prompt_template: 提示词模板
            
        Returns:
            总结结果
        """
        if not self.client:
            print("DeepSeek API密钥未配置")
            return None
        
        try:
            # 构建提示词
            prompt = self._build_prompt(text, prompt_template)
            
            # 从配置获取参数
            model = self.config.get('model', 'deepseek-chat')
            max_tokens = self.config.get('max_tokens', 2000)
            temperature = self.config.get('temperature', 0.7)
            system_prompt = self.config.get('system_prompt', '')
            
            # 构建消息
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 调用API
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            summary = response.choices[0].message.content.strip()
            print("DeepSeek总结完成")
            return summary
            
        except Exception as e:
            print(f"DeepSeek总结失败: {str(e)}")
            return None

