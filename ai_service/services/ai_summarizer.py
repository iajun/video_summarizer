"""
AI总结服务模块
负责使用多种AI服务进行内容总结
使用新的 ai_providers 模块，支持策略模式和工厂模式
"""

from typing import Optional
from ..utils import S3Client
from ..utils.task_queue import run_io_blocking, run_io_bound, run_coro_blocking
import asyncio


class AISummarizer:
    """AI总结服务 - 使用 ai_providers 模块"""
    
    def __init__(self, api_key: Optional[str] = None, method_name: Optional[str] = None):
        """初始化AI总结服务
        
        Args:
            api_key: API密钥（用于token方式，向后兼容）
            method_name: 使用的方法名称 (deepseek, chatgpt, yuanbao)，如果为None则从数据库读取
        """
        self.api_key = api_key
        self.s3_client = S3Client()
        self.method_name = method_name or self._get_active_method_name() or "deepseek"
        self._provider = None
    
    def _get_active_method_name(self) -> str:
        """从数据库读取当前活跃的AI方法名称"""
        try:
            from ..db import get_db_session
            from ..models import AIMethod
            
            with get_db_session() as db:
                method = db.query(AIMethod).filter(AIMethod.is_active == 1).first()
                if method:
                    print(f"Using active AI method: {method.name}")
                    return method.name
        except Exception as e:
            print(f"Failed to load active AI method: {e}")
        
        return "deepseek"
    
    def _get_provider_config(self, method_config: Optional[dict] = None) -> dict:
        """获取提供者配置"""
        config = method_config or {}
        
        # 如果没有在method_config中提供，尝试从数据库读取
        if not config.get('api_key') and self.method_name == 'deepseek':
            if self.api_key:
                config['api_key'] = self.api_key
            else:
                try:
                    from ..db import get_db_session
                    from ..models import AIMethod
                    
                    with get_db_session() as db:
                        method = db.query(AIMethod).filter(AIMethod.name == self.method_name).first()
                        if method and method.api_key:
                            config['api_key'] = method.api_key
                except Exception as e:
                    print(f"Failed to load API key from database: {e}")
        
        if not config.get('cookies') and self.method_name in ['chatgpt', 'yuanbao']:
            try:
                from ..db import get_db_session
                from ..models import AIMethod
                
                with get_db_session() as db:
                    method = db.query(AIMethod).filter(AIMethod.name == self.method_name).first()
                    if method and method.cookies:
                        config['cookies'] = method.cookies
            except Exception as e:
                print(f"Failed to load cookies from database: {e}")
        
        # 从数据库读取AI参数
        try:
            from ..db import get_db_session
            from ..models import Setting
            
            with get_db_session() as db:
                # max_tokens
                setting = db.query(Setting).filter(Setting.key == "ai_max_tokens").first()
                if setting and setting.value:
                    config['max_tokens'] = int(setting.value)
                
                # temperature
                setting = db.query(Setting).filter(Setting.key == "ai_temperature").first()
                if setting and setting.value:
                    config['temperature'] = float(setting.value)
                
                # model
                setting = db.query(Setting).filter(Setting.key == "ai_model").first()
                if setting and setting.value:
                    config['model'] = setting.value
                
                # system_prompt
                setting = db.query(Setting).filter(Setting.key == "ai_system_prompt").first()
                if setting and setting.value:
                    config['system_prompt'] = setting.value
        except Exception as e:
            print(f"Failed to load AI settings from database: {e}")
        
        return config
    
    def _get_default_prompt_template(self) -> Optional[str]:
        """获取默认提示词模板（包含{text}占位符）"""
        prompt_info = self._get_default_prompt_info()
        return prompt_info['content'] if prompt_info else None
    
    def _get_default_prompt_info(self) -> Optional[dict]:
        """获取默认提示词信息（包含名称和内容）"""
        # 首先尝试从 prompts 表获取默认提示词
        try:
            from ..db import get_db_session
            from ..models import Prompt
            
            with get_db_session() as db:
                default_prompt = db.query(Prompt).filter(Prompt.is_default == 1).first()
                if default_prompt and default_prompt.content:
                    return {
                        'name': default_prompt.name,
                        'content': default_prompt.content
                    }
        except Exception as e:
            print(f"Failed to load default prompt from prompts table: {e}")
        
        # 尝试从数据库 Setting 读取（兼容旧数据）
        try:
            from ..db import get_db_session
            from ..models import Setting
            
            with get_db_session() as db:
                setting = db.query(Setting).filter(Setting.key == "ai_prompt_template").first()
                if setting and setting.value:
                    return {
                        'name': '默认提示词',
                        'content': setting.value
                    }
        except Exception as e:
            print(f"Failed to load prompt from database: {e}")
        
        return None
    
    def summarize_with_ai(
        self,
        text: str,
        video_id: str,
        force_regenerate: bool = False,
        custom_prompt: Optional[str] = None,
        method_config: Optional[dict] = None
    ) -> Optional[str]:
        """使用AI进行内容总结（同步接口，向后兼容）
        
        Args:
            text: 要总结的文本
            video_id: 视频ID
            force_regenerate: 是否强制重新生成，即使S3中已存在总结
            custom_prompt: 自定义提示词（可选，用户调试时使用）
            method_config: AI方法配置（可选，包含api_key, cookies等）
        """
        # 在线程池中运行异步方法（使用 run_coro_blocking 来正确处理 coroutine）
        return run_coro_blocking(
            self.summarize_with_ai_async,
            text,
            video_id,
            force_regenerate,
            custom_prompt,
            method_config
        )
    
    async def summarize_with_ai_async(
        self,
        text: str,
        video_id: str,
        force_regenerate: bool = False,
        custom_prompt: Optional[str] = None,
        method_config: Optional[dict] = None
    ) -> Optional[str]:
        """使用AI进行内容总结（异步接口）
        
        Args:
            text: 要总结的文本
            video_id: 视频ID
            force_regenerate: 是否强制重新生成
            custom_prompt: 自定义提示词
            method_config: AI方法配置
        """
        try:
            # 导入 ai_providers
            from ai_providers import get_provider
            
            # 获取提供者配置
            config = self._get_provider_config(method_config)
            
            # 创建提供者实例
            provider = get_provider(self.method_name, config=config)
            if not provider:
                print(f"无法创建AI提供者: {self.method_name}")
                return None
            
            # 获取提示词模板
            prompt_template = custom_prompt or self._get_default_prompt_template()
            
            # 调用提供者的总结方法
            if provider.get_provider_type() == 'api':
                # API方式：直接异步调用
                summary = await provider.summarize(text, prompt_template)
            else:
                # 浏览器方式：需要在线程池中运行（因为可能从同步上下文调用）
                summary = await run_io_bound(
                    self._run_browser_provider,
                    provider,
                    text,
                    prompt_template
                )
            
            if summary:
                print(f"{self.method_name}总结完成")
                return summary
            else:
                print(f"{self.method_name}总结失败")
                return None
                
        except Exception as e:
            print(f"AI总结失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _run_browser_provider(self, provider, text: str, prompt_template: Optional[str]) -> Optional[str]:
        """在线程中运行浏览器提供者（因为需要事件循环）"""
        async def run():
            async with provider:
                return await provider.summarize(text, prompt_template)
        
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run())
        finally:
            loop.close()
