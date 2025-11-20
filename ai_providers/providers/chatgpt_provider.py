"""
ChatGPT 浏览器提供者
使用Playwright访问ChatGPT进行文本总结
"""

from typing import Optional
from .browser_provider import BrowserAIProvider


class ChatGPTProvider(BrowserAIProvider):
    """ChatGPT浏览器提供者"""
    
    def __init__(self, cookies: Optional[str] = None, config: Optional[dict] = None):
        """
        初始化ChatGPT提供者
        
        Args:
            cookies: ChatGPT Cookies（JSON格式或分号分隔）
            config: 额外配置
        """
        super().__init__(
            name="ChatGPT",
            chat_url="https://chat.openai.com",
            cookies=cookies,
            config=config
        )
    
    def _get_headless_mode(self) -> bool:
        return True
    
    def _get_input_selectors(self) -> list[str]:
        return ['#prompt-textarea']
    
    def _get_submit_selectors(self) -> list[str]:
        return ['composer-submit-button']
    
    def _get_wait_success_selector(self) -> Optional[str]:
        return '#thread article:nth-child(2) button[aria-label="Copy"]'
    
    def _get_copy_button_selectors(self) -> list[str]:
        return ['#thread article:nth-child(2) button[aria-label="Copy"]']

