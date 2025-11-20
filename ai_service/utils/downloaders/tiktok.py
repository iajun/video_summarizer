"""
TikTok/Douyin 视频下载器
使用 tiktok_downloader 模块下载视频
"""
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

from tiktok_downloader.src.application import TikTokDownloader
from tiktok_downloader.src.application.main_terminal import TikTok

from .base import BaseDownloader, DownloadResult
from ..url_detector import detect_platform


class TikTokDownloader(BaseDownloader):
    """TikTok/Douyin 视频下载器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 TikTok/Douyin 下载器
        
        Args:
            config: 配置字典，可包含 'tiktok_downloader' 实例
        """
        super().__init__(config)
        self.downloader = self.config.get('tiktok_downloader')
        self.tiktok_instance = None
    
    async def extract_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """提取视频信息（不下载）"""
        if not self.downloader:
            return None
        
        try:
            # 初始化下载器
            self.downloader.project_info()
            self.downloader.check_config()
            await self.downloader.check_settings(False)
            
            self.tiktok_instance = TikTok(self.downloader.parameter, self.downloader.database)
            
            # 检测平台
            platform = detect_platform(url)
            is_tiktok = (platform == 'tiktok')
            
            # 提取视频ID
            run_method = self.tiktok_instance.links_tiktok.run if is_tiktok else self.tiktok_instance.links.run
            ids = await run_method(url)
            
            if not ids:
                return None
            
            # 获取视频详情
            detail_data, _ = await self._get_video_details(ids, is_tiktok)
            
            return detail_data[0] if detail_data and len(detail_data) > 0 else None
            
        except Exception as e:
            print(f"提取视频信息失败: {e}")
            return None
    
    async def download_video(
        self,
        url: str,
        output_dir: Optional[str] = None,
        force_download: bool = False
    ) -> DownloadResult:
        """下载视频"""
        if not self.downloader:
            return DownloadResult(
                video_path=None,
                video_info=None,
                video_id='',
                platform=detect_platform(url),
                success=False,
                error="TikTok下载器未初始化"
            )
        
        try:
            # 初始化下载器
            self.downloader.project_info()
            self.downloader.check_config()
            await self.downloader.check_settings(False)
            
            if output_dir:
                self.downloader.parameter.root = Path(output_dir)
            
            self.tiktok_instance = TikTok(self.downloader.parameter, self.downloader.database)
            
            # 检测平台
            platform = detect_platform(url)
            is_tiktok = (platform == 'tiktok')
            
            # 提取视频ID
            run_method = self.tiktok_instance.links_tiktok.run if is_tiktok else self.tiktok_instance.links.run
            ids = await run_method(url)
            
            if not ids:
                return DownloadResult(
                    video_path=None,
                    video_info=None,
                    video_id='',
                    platform=platform,
                    success=False,
                    error=f"无法从URL提取视频ID: {url}"
                )
            
            video_id = ids[0] if isinstance(ids, list) else str(ids)
            detail_data, video_name = await self._get_video_details(ids, is_tiktok)
            
            if not detail_data:
                return DownloadResult(
                    video_path=None,
                    video_info=None,
                    video_id=video_id,
                    platform=platform,
                    success=False,
                    error="无法获取视频详情"
                )
            
            # 转换为统一格式
            detail_dict = self._convert_detail_data_to_dict(detail_data, url, video_id, platform)
            
            # 执行下载
            if force_download:
                await self._clean_existing_files(video_name, video_id)
            
            print("开始下载视频...")
            await self.tiktok_instance.downloader.run(detail_data, "detail", tiktok=is_tiktok)
            
            # 查找下载的视频文件
            video_path = await self._find_downloaded_video(video_name)
            
            if video_path:
                return DownloadResult(
                    video_path=video_path,
                    video_info=detail_dict,
                    video_id=video_id,
                    platform=platform,
                    success=True
                )
            else:
                return DownloadResult(
                    video_path=None,
                    video_info=detail_dict,
                    video_id=video_id,
                    platform=platform,
                    success=False,
                    error="未找到下载的视频文件"
                )
                
        except Exception as e:
            print(f"下载视频失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return DownloadResult(
                video_path=None,
                video_info=None,
                video_id='',
                platform=detect_platform(url),
                success=False,
                error=str(e)
            )
    
    def extract_video_id(self, url: str, video_info: Optional[Dict[str, Any]] = None) -> str:
        """从 URL 或信息中提取视频 ID"""
        if video_info and isinstance(video_info, dict):
            video_id = video_info.get('id') or video_info.get('aweme_id')
            if video_id:
                return str(video_id)
        
        # 从 URL 中提取
        import re
        video_id_match = re.search(r'/video/(\d+)', url)
        if video_id_match:
            return video_id_match.group(1)
        
        # 如果都提取不到，使用 URL 的哈希值
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return 'tiktok'  # 或 'douyin'，取决于实际URL
    
    def supports_url(self, url: str) -> bool:
        """检查是否支持该URL"""
        platform = detect_platform(url)
        return platform in ['tiktok', 'douyin']
    
    async def _get_video_details(self, ids, is_tiktok: bool) -> tuple[Optional[List], str]:
        """获取视频详情和名称"""
        root, params, logger = self.tiktok_instance.record.run(self.downloader.parameter)
        async with logger(root, console=self.downloader.console, **params) as record:
            detail_data = await self.tiktok_instance._handle_detail(ids, is_tiktok, record, api=True)
            video_name = self._get_video_name_from_detail_data(detail_data, ids)
        return detail_data, video_name
    
    def _get_video_name_from_detail_data(self, detail_data: List, ids) -> str:
        """从detail_data中提取视频名称"""
        try:
            if detail_data and len(detail_data) > 0 and isinstance(detail_data[0], dict):
                return self.tiktok_instance.downloader.generate_detail_name(detail_data[0])
            else:
                return ids[0] if isinstance(ids, list) else str(ids)
        except Exception as e:
            print(f"提取视频名称失败: {str(e)}")
            return ids[0] if isinstance(ids, list) else str(ids)
    
    async def _clean_existing_files(self, video_name: str, video_id: str):
        """清理已存在的文件和记录"""
        download_dir = Path(self.downloader.parameter.root) / "Download"
        
        safe_name = video_name
        
        # 清理文件
        if self.downloader.parameter.folder_mode:
            video_folder = download_dir / safe_name
            if video_folder.exists():
                shutil.rmtree(video_folder, ignore_errors=True)
        else:
            for ext in ['.mp4', '.mov', '.avi']:
                file_path = download_dir / f"{safe_name}{ext}"
                if file_path.exists():
                    file_path.unlink()
        
        # 清理数据库记录
        print(f"正在清理视频 {video_id} 的数据库记录...")
        if hasattr(self.downloader, 'recorder') and self.downloader.recorder:
            try:
                has_record = await self.downloader.recorder.has_id(video_id)
                if has_record:
                    await self.downloader.recorder.delete_id(video_id)
                    print(f"✓ 已清理数据库记录: {video_id}")
                else:
                    print(f"  数据库中不存在记录: {video_id}")
            except Exception as e:
                print(f"清理数据库记录失败: {str(e)}")
        else:
            print("recorder 不可用，跳过数据库清理")
    
    async def _find_downloaded_video(self, video_name: str) -> Optional[str]:
        """查找已下载的视频文件"""
        try:
            download_dir = Path(self.downloader.parameter.root) / "Download"
            
            if not download_dir.exists():
                return None
            
            safe_name = video_name
            video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm']
            
            # 如果启用了文件夹模式，在文件夹内查找
            if (hasattr(self.downloader.parameter, 'folder_mode') and 
                self.downloader.parameter.folder_mode):
                video_folder = download_dir / safe_name
                if video_folder.exists() and video_folder.is_dir():
                    for ext in video_extensions:
                        video_file = video_folder / f"{safe_name}{ext}"
                        if video_file.exists() and video_file.is_file():
                            return str(video_file.resolve())
            
            # 非文件夹模式，直接在目录中查找
            for ext in video_extensions:
                video_file = download_dir / f"{safe_name}{ext}"
                if video_file.exists() and video_file.is_file():
                    return str(video_file.resolve())
            
            return None
            
        except Exception as e:
            print(f"查找下载的视频文件失败: {e}")
            return None
    
    def _convert_detail_data_to_dict(self, detail_data: List, url: str, video_id: str, platform: str) -> Dict[str, Any]:
        """将detail_data转换为字典格式"""
        try:
            if not detail_data or len(detail_data) == 0:
                return {}
            
            detail = detail_data[0] if isinstance(detail_data, list) else detail_data
            
            # 提取text_extra标签
            text_extra = []
            if isinstance(detail.get('text_extra'), list):
                text_extra = [tag.get('hashtag_name', '') for tag in detail.get('text_extra', []) if isinstance(tag, dict)]
            
            # 提取tag
            tag = []
            if isinstance(detail.get('tag'), list):
                tag = detail.get('tag', [])
            
            raw_info = {
                'title': detail.get('desc', ''),
                'description': detail.get('desc', ''),
                'text_extra': text_extra,
                'tag': tag,
                'type': detail.get('type', ''),
                'height': detail.get('height', 0),
                'width': detail.get('width', 0),
                'duration': detail.get('duration', ''),
                'uri': detail.get('uri', ''),
                'downloads': detail.get('downloads', ''),
                'dynamic_cover': detail.get('dynamic_cover', ''),
                'static_cover': detail.get('static_cover', ''),
                'uid': detail.get('uid', ''),
                'sec_uid': detail.get('sec_uid', ''),
                'unique_id': detail.get('unique_id', ''),
                'signature': detail.get('signature', ''),
                'user_age': detail.get('user_age', 0),
                'nickname': detail.get('nickname', ''),
                'mark': detail.get('mark', ''),
                'music_author': detail.get('music_author', ''),
                'music_title': detail.get('music_title', ''),
                'music_url': detail.get('music_url', ''),
                'digg_count': detail.get('digg_count', 0),
                'comment_count': detail.get('comment_count', 0),
                'collect_count': detail.get('collect_count', 0),
                'share_count': detail.get('share_count', 0),
                'play_count': detail.get('play_count', -1),
                'share_url': detail.get('share_url', ''),
            }
            
            return self.normalize_video_info(raw_info, url, video_id)
            
        except Exception as e:
            print(f"转换detail_data失败: {str(e)}")
            return {}

