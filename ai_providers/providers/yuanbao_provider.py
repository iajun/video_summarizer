"""
腾讯元宝 浏览器提供者
使用Playwright访问腾讯元宝进行文本总结
"""

from typing import Optional
from .browser_provider import BrowserAIProvider


class YuanBaoProvider(BrowserAIProvider):
    """腾讯元宝浏览器提供者"""
    
    def __init__(self, cookies: Optional[str] = None, config: Optional[dict] = None):
        """
        初始化腾讯元宝提供者
        
        Args:
            cookies: 腾讯元宝Cookies（JSON格式或分号分隔）
            config: 额外配置
        """
        super().__init__(
            name="腾讯元宝",
            chat_url="https://yuanbao.tencent.com",
            cookies=cookies,
            config=config
        )
    
    def _get_headless_mode(self) -> bool:
        return True
    
    def _get_input_selectors(self) -> list[str]:
        return ['.chat-input-editor > .ql-editor']
    
    async def _init_page(self):
        """初始化页面：点击深度思考按钮"""
        if button := await self.page.query_selector('div[dt-button-id="deep_think"]'):
            await button.click()
    
    def _get_submit_selectors(self) -> list[str]:
        return ['#yuanbao-send-btn']
    
    def _get_wait_success_selector(self) -> Optional[str]:
        return '#chat-content div.agent-chat__toolbar__copy__arrow-container > span'
    
    def _get_copy_button_selectors(self) -> list[str]:
        return [
            '#chat-content div.agent-chat__toolbar__copy__arrow-container > span',
            '#hunyuan-bot > div.t-portal-wrapper.enter-done > div > div > div > div:nth-child(2) > li > span'
        ]
    
    async def _check_login_status(self):
        """检查登录状态"""
        page_content = await self.page.content()
        if "login" in self.page.url.lower() or "未登录" in page_content:
            print("检测到需要登录，请确保cookies有效")

