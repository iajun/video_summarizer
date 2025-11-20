"""
下载器工厂
根据URL自动选择合适的下载器
"""
from typing import Optional, Dict, Any
from .base import BaseDownloader
from .bilibili import BilibiliDownloader
from .tiktok import TikTokDownloader
from ..url_detector import detect_platform


class DownloaderFactory:
    """下载器工厂类"""
    
    # 注册的下载器类
    _downloaders: Dict[str, type] = {
        'bilibili': BilibiliDownloader,
        'tiktok': TikTokDownloader,
        'douyin': TikTokDownloader,  # Douyin 和 TikTok 使用同一个下载器
    }
    
    @classmethod
    def register_downloader(cls, platform: str, downloader_class: type):
        """
        注册新的下载器
        
        Args:
            platform: 平台名称
            downloader_class: 下载器类（必须继承 BaseDownloader）
        """
        if not issubclass(downloader_class, BaseDownloader):
            raise TypeError(f"下载器类必须继承 BaseDownloader")
        cls._downloaders[platform] = downloader_class
    
    @classmethod
    def create_downloader(
        cls,
        url: Optional[str] = None,
        platform: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseDownloader]:
        """
        创建下载器实例
        
        Args:
            url: 视频URL（用于自动检测平台）
            platform: 平台名称（如果提供则直接使用）
            config: 下载器配置
            
        Returns:
            下载器实例，如果不支持则返回 None
        """
        # 确定平台
        if platform:
            platform_name = platform.lower()
        elif url:
            platform_name = detect_platform(url)
        else:
            return None
        
        # 如果平台未知，返回 None
        if platform_name == 'unknown':
            return None
        
        # 获取下载器类
        downloader_class = cls._downloaders.get(platform_name)
        if not downloader_class:
            return None
        
        # 创建实例
        try:
            return downloader_class(config=config)
        except Exception as e:
            print(f"创建下载器失败 ({platform_name}): {e}")
            return None
    
    @classmethod
    def get_supported_platforms(cls) -> list:
        """
        获取所有支持的平台列表
        
        Returns:
            平台名称列表
        """
        return list(cls._downloaders.keys())


def get_downloader(
    url: Optional[str] = None,
    platform: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Optional[BaseDownloader]:
    """
    便捷函数：获取下载器实例
    
    Args:
        url: 视频URL
        platform: 平台名称
        config: 下载器配置
        
    Returns:
        下载器实例
    """
    return DownloaderFactory.create_downloader(url=url, platform=platform, config=config)

