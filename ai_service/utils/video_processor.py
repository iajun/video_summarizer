"""
视频处理模块
负责视频下载协调、缓存管理等功能
使用统一的下载器架构，支持多平台扩展
"""
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from tiktok_downloader.src.application import TikTokDownloader
from .s3_client import S3Client
from .task_queue import run_io_bound
from .url_detector import detect_platform
from .downloaders import get_downloader, DownloadResult


class VideoProcessor:
    """视频处理器 - 协调下载流程和缓存管理"""
    
    def __init__(self, downloader: TikTokDownloader, bilibili_cookies: Optional[str] = None):
        """
        初始化视频处理器
        
        Args:
            downloader: TikTok下载器实例（用于 TikTok/Douyin 平台）
            bilibili_cookies: Bilibili Cookie 文件路径或内容
        """
        self.downloader = downloader
        self.s3_client = S3Client()
        self.bilibili_cookies = bilibili_cookies
    
    async def download_video(
        self,
        url: str,
        output_dir: Optional[str] = None,
        force_download: bool = False
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """
        下载视频并返回视频文件路径和详情数据
        
        Args:
            url: 视频URL
            output_dir: 输出目录
            force_download: 是否强制重新下载
            
        Returns:
            tuple: (本地视频路径, 视频详情数据字典, 视频ID)
        """
        try:
            print(f"开始下载视频: {url}")
            
            # 检测平台
            platform = detect_platform(url)
            if platform == 'unknown':
                print(f"不支持的平台: {url}")
                return None, None, None
            
            # 创建下载器配置
            config = self._build_downloader_config(platform, output_dir)
            
            # 获取下载器实例
            platform_downloader = get_downloader(url=url, platform=platform, config=config)
            if not platform_downloader:
                print(f"无法创建下载器: {platform}")
                return None, None, None
            
            # 先提取视频信息（用于获取 video_id）
            video_info = await platform_downloader.extract_video_info(url)
            if not video_info:
                print("无法获取视频信息")
                return None, None, None
            
            # 提取视频ID
            video_id = platform_downloader.extract_video_id(url, video_info)
            
            # 检查缓存（本地和S3）
            if not force_download:
                # 检查本地缓存
                local_path = await self._check_local_cache(video_id)
                if local_path:
                    print(f"找到本地缓存: {local_path}")
                    # 获取视频信息
                    normalized_info = platform_downloader.normalize_video_info(
                        video_info, url, video_id
                    )
                    return local_path, normalized_info, video_id
                
                # 检查S3缓存
                s3_path = await self._check_s3_cache(video_id)
                if s3_path:
                    print(f"找到S3缓存: {s3_path}")
                    local_path = await self._download_from_s3_to_local(s3_path, video_id, output_dir)
                    if local_path:
                        normalized_info = platform_downloader.normalize_video_info(
                            video_info, url, video_id
                        )
                        return local_path, normalized_info, video_id
            
            # 执行下载
            print("开始下载视频...")
            result = await platform_downloader.download_video(
                url=url,
                output_dir=output_dir,
                force_download=force_download
            )
            
            if result.success and result.video_path:
                print(f"视频下载成功: {result.video_path}")
                return result.video_path, result.video_info, result.video_id
            else:
                error_msg = result.error or "下载失败"
                print(f"视频下载失败: {error_msg}")
                return None, result.video_info, result.video_id
                
        except Exception as e:
            print(f"下载视频失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None, None
    
    def _build_downloader_config(self, platform: str, output_dir: Optional[str]) -> Dict[str, Any]:
        """
        构建下载器配置
        
        Args:
            platform: 平台名称
            output_dir: 输出目录
            
        Returns:
            配置字典
        """
        config = {}
        
        # Bilibili 配置
        if platform == 'bilibili' and self.bilibili_cookies:
            config['cookies'] = self.bilibili_cookies
        
        # TikTok/Douyin 配置
        if platform in ['tiktok', 'douyin']:
            config['tiktok_downloader'] = self.downloader
        
        return config
    
    async def _check_local_cache(
        self,
        video_id: str,
    ) -> Optional[str]:
        """
        检查本地缓存
        
        Args:
            video_id: 视频ID
            downloader: 下载器实例
            url: 视频URL
            
        Returns:
            本地视频文件路径，如果不存在则返回 None
        """
        try:
            # 确定下载目录
            if self.downloader and hasattr(self.downloader, 'parameter'):
                download_dir = Path(self.downloader.parameter.root) / "Download"
            else:
                from tiktok_downloader.src.custom import PROJECT_ROOT
                download_dir = PROJECT_ROOT / "Download"
            
            if not download_dir.exists():
                return None
            
            # 支持的视频文件扩展名
            video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm']
            
            # 首先尝试使用 video_id 查找
            for ext in video_extensions:
                video_file = download_dir / f"{video_id}{ext}"
                if video_file.exists() and video_file.is_file():
                    return str(video_file.resolve())
            
            # 对于 TikTok/Douyin，可能需要通过视频名称查找
            # 这里简化处理，如果需要可以扩展
            # 暂时返回 None，让下载器自己处理
            
            return None
            
        except Exception as e:
            print(f"检查本地缓存失败: {e}")
            return None
    
    async def _check_s3_cache(self, video_id: str) -> Optional[str]:
        """
        检查S3缓存
        
        Args:
            video_id: 视频ID
            
        Returns:
            S3路径，如果不存在则返回 None
        """
        try:
            s3_video_path = f"videos/{video_id}.mp4"
            s3_exists = await run_io_bound(self.s3_client.file_exists, s3_video_path)
            if s3_exists:
                return s3_video_path
            return None
        except Exception as e:
            print(f"检查S3缓存失败: {e}")
            return None
    
    async def _download_from_s3_to_local(self, s3_path: str, video_id: str, output_dir: str) -> Optional[str]:
        """
        从S3下载文件到本地
        
        Args:
            s3_path: S3路径
            video_id: 视频ID
            
        Returns:
            local_path: 本地文件路径
        """
        try:
            local_path = Path(output_dir) / f"{video_id}.mp4"
            success = await run_io_bound(self.s3_client.download_file, s3_path, str(local_path))
            if success:
                return str(local_path)
            return None
        except Exception as e:
            print(f"从S3下载文件失败: {e}")
            return None
