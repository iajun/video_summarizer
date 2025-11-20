"""
下载器基类接口
定义所有平台下载器必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class DownloadResult:
    """下载结果"""
    video_path: Optional[str]  # 本地视频文件路径
    video_info: Optional[Dict[str, Any]]  # 视频详情信息（统一格式）
    video_id: str  # 视频ID
    platform: str  # 平台名称
    success: bool  # 是否成功
    error: Optional[str] = None  # 错误信息


class BaseDownloader(ABC):
    """下载器基类，所有平台下载器必须继承此类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化下载器
        
        Args:
            config: 下载器配置（如 cookies、api_key 等）
        """
        self.config = config or {}
    
    @abstractmethod
    async def extract_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        提取视频信息（不下载）
        
        Args:
            url: 视频URL
            
        Returns:
            视频信息字典，包含 title, description, video_id 等
        """
        pass
    
    @abstractmethod
    async def download_video(
        self,
        url: str,
        output_dir: Optional[str] = None,
        force_download: bool = False
    ) -> DownloadResult:
        """
        下载视频
        
        Args:
            url: 视频URL
            output_dir: 输出目录
            force_download: 是否强制重新下载
            
        Returns:
            DownloadResult 对象
        """
        pass
    
    @abstractmethod
    def extract_video_id(self, url: str, video_info: Optional[Dict[str, Any]] = None) -> str:
        """
        从URL或视频信息中提取视频ID
        
        Args:
            url: 视频URL
            video_info: 视频信息（可选）
            
        Returns:
            视频ID字符串
        """
        pass
    
    def normalize_video_info(
        self,
        raw_info: Dict[str, Any],
        url: str,
        video_id: str
    ) -> Dict[str, Any]:
        """
        将平台特定的视频信息转换为统一格式
        
        Args:
            raw_info: 平台原始视频信息
            url: 视频URL
            video_id: 视频ID
            
        Returns:
            统一格式的视频信息字典
        """
        return {
            'id': video_id,
            'url': url,
            'platform': self.get_platform_name(),
            'title': raw_info.get('title', ''),
            'desc': raw_info.get('description', '') or raw_info.get('desc', ''),
            'text_extra': raw_info.get('text_extra', []),
            'tag': raw_info.get('tag', []),
            'type': raw_info.get('type', 'video'),
            'height': raw_info.get('height', 0),
            'width': raw_info.get('width', 0),
            'duration': raw_info.get('duration', ''),
            'uri': raw_info.get('uri', url),
            'downloads': raw_info.get('downloads', ''),
            'dynamic_cover': raw_info.get('dynamic_cover') or raw_info.get('thumbnail', ''),
            'static_cover': raw_info.get('static_cover') or raw_info.get('thumbnail', ''),
            'uid': raw_info.get('uid', '') or raw_info.get('uploader_id', ''),
            'sec_uid': raw_info.get('sec_uid', ''),
            'unique_id': raw_info.get('unique_id', '') or raw_info.get('uploader', ''),
            'signature': raw_info.get('signature', ''),
            'user_age': raw_info.get('user_age', 0),
            'nickname': raw_info.get('nickname', '') or raw_info.get('uploader', ''),
            'mark': raw_info.get('mark', ''),
            'music_author': raw_info.get('music_author', ''),
            'music_title': raw_info.get('music_title', ''),
            'music_url': raw_info.get('music_url', ''),
            'digg_count': raw_info.get('digg_count', 0),
            'comment_count': raw_info.get('comment_count', 0),
            'collect_count': raw_info.get('collect_count', 0),
            'share_count': raw_info.get('share_count', 0),
            'play_count': raw_info.get('play_count', -1),
            'share_url': raw_info.get('share_url', url),
        }
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """
        获取平台名称
        
        Returns:
            平台名称字符串（如 'bilibili', 'tiktok', 'douyin'）
        """
        pass
    
    @abstractmethod
    def supports_url(self, url: str) -> bool:
        """
        检查是否支持该URL
        
        Args:
            url: 视频URL
            
        Returns:
            如果支持返回 True
        """
        pass

