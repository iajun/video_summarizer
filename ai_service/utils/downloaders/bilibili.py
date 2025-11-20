"""
Bilibili 视频下载器
使用 you-get 库下载 Bilibili 视频
"""
import json
import os
import subprocess
import tempfile
import re
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import shutil

from .base import BaseDownloader, DownloadResult
from ..task_queue import run_io_bound


class BilibiliDownloader(BaseDownloader):
    """Bilibili 视频下载器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Bilibili 下载器
        
        Args:
            config: 配置字典，可包含 'cookies' 字段
        """
        super().__init__(config)
        
        # 检查 you-get 是否安装
        self.you_get_cmd = shutil.which('you-get')
        if not self.you_get_cmd:
            # 尝试使用 python -m you_get
            try:
                import sys
                result = subprocess.run(
                    [sys.executable, '-m', 'you_get', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.you_get_cmd = [sys.executable, '-m', 'you_get']
                else:
                    raise ImportError("you-get is not installed. Please install it with: pip install you-get")
            except Exception:
                raise ImportError("you-get is not installed. Please install it with: pip install you-get")
        
        # 处理 cookies
        self.cookies = self.config.get('cookies')
        self.cookies_file = None
        self._temp_cookies_file = False
        
        if self.cookies:
            if os.path.exists(self.cookies):
                # 如果是文件路径
                self.cookies_file = self.cookies
            else:
                # 如果是 Cookie 内容字符串，创建临时文件
                self._create_temp_cookies_file(self.cookies)
    
    def _create_temp_cookies_file(self, cookies_content: str):
        """创建临时 Cookie 文件"""
        try:
            temp_dir = Path(tempfile.gettempdir()) / "ai_service_bilibili"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            self.cookies_file = temp_dir / "cookies.txt"
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                f.write(cookies_content)
            self._temp_cookies_file = True
        except Exception as e:
            print(f"创建临时 Cookie 文件失败: {e}")
            self.cookies_file = None
    
    async def extract_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """提取视频信息（不下载）"""
        return await run_io_bound(self._extract_video_info_sync, url)
    
    def _extract_video_info_sync(self, url: str) -> Optional[Dict[str, Any]]:
        """同步提取视频信息"""
        try:
            cmd = self._build_cmd(url, info_only=False, json_output=True)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    output = result.stdout.strip()
                    json_start = output.find('{')
                    if json_start == -1:
                        if result.stderr:
                            output = result.stderr.strip()
                            json_start = output.find('{')
                    
                    if json_start >= 0:
                        json_end = output.rfind('}') + 1
                        if json_end > json_start:
                            json_str = output[json_start:json_end]
                            try:
                                return json.loads(json_str)
                            except json.JSONDecodeError:
                                json_str = json_str.rstrip().rstrip(',')
                                if json_str.endswith('}'):
                                    try:
                                        return json.loads(json_str)
                                    except json.JSONDecodeError:
                                        pass
                    
                    try:
                        return json.loads(output)
                    except json.JSONDecodeError:
                        pass
                    
                    print(f"无法解析 JSON 输出，输出内容: {output[:500]}")
                    return None
                except json.JSONDecodeError as e:
                    print(f"解析 JSON 输出失败: {e}")
                    return None
            else:
                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or ''
                    if 'not allowed with argument' in error_msg or '--json' in error_msg:
                        print(f"--json 参数不可用，回退到文本解析")
                        return self._extract_info_from_text(url)
                    else:
                        print(f"获取视频信息失败 (code {result.returncode}): {error_msg[:200]}")
                        return self._extract_info_from_text(url)
                return None
                
        except subprocess.TimeoutExpired:
            print("获取视频信息超时")
            return None
        except Exception as e:
            print(f"提取视频信息失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_info_from_text(self, url: str) -> Optional[Dict[str, Any]]:
        """从文本输出中提取视频信息（备用方法）"""
        try:
            cmd = self._build_cmd(url, info_only=True, json_output=False)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                info = {
                    'site': 'Bilibili',
                    'title': '',
                    'streams': {}
                }
                
                current_stream = None
                for line in lines:
                    line = line.strip()
                    if line.startswith('site:'):
                        info['site'] = line.split(':', 1)[1].strip()
                    elif line.startswith('title:'):
                        info['title'] = line.split(':', 1)[1].strip()
                    elif line.startswith('- format:'):
                        format_id = line.split(':', 1)[1].strip()
                        current_stream = {
                            'format': format_id,
                            'container': '',
                            'quality': '',
                            'size': ''
                        }
                    elif line.startswith('container:') and current_stream:
                        current_stream['container'] = line.split(':', 1)[1].strip()
                    elif line.startswith('quality:') and current_stream:
                        current_stream['quality'] = line.split(':', 1)[1].strip()
                    elif line.startswith('size:') and current_stream:
                        size_str = line.split(':', 1)[1].strip()
                        current_stream['size'] = size_str
                        if current_stream.get('format'):
                            info['streams'][current_stream['format']] = current_stream
                            current_stream = None
                
                if info.get('title'):
                    return info
                    
            return None
            
        except Exception as e:
            print(f"从文本提取信息失败: {e}")
            return None
    
    async def download_video(
        self,
        url: str,
        output_dir: Optional[str] = None,
        force_download: bool = False
    ) -> DownloadResult:
        """下载视频"""
        try:
            # 先获取视频信息
            info = await self.extract_video_info(url)
            if not info:
                return DownloadResult(
                    video_path=None,
                    video_info=None,
                    video_id='',
                    platform='bilibili',
                    success=False,
                    error="无法获取视频信息"
                )
            
            # 提取视频ID
            video_id = self.extract_video_id(url, info)
            
            # 转换为统一格式
            video_info = self._convert_bilibili_info_to_dict(info, url, video_id)
            
            # 设置输出目录
            if output_dir:
                download_dir = Path(output_dir) / "Download"
            else:
                from tiktok_downloader.src.custom import PROJECT_ROOT
                download_dir = PROJECT_ROOT / "Download"
            
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # 执行下载
            video_path, _ = await run_io_bound(
                self._download_video_sync,
                url,
                str(download_dir),
                video_id
            )
            
            if video_path:
                return DownloadResult(
                    video_path=video_path,
                    video_info=video_info,
                    video_id=video_id,
                    platform='bilibili',
                    success=True
                )
            else:
                return DownloadResult(
                    video_path=None,
                    video_info=video_info,
                    video_id=video_id,
                    platform='bilibili',
                    success=False,
                    error="下载失败或未找到视频文件"
                )
                
        except Exception as e:
            print(f"下载 Bilibili 视频失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return DownloadResult(
                video_path=None,
                video_info=None,
                video_id='',
                platform='bilibili',
                success=False,
                error=str(e)
            )
    
    def _download_video_sync(
        self,
        url: str,
        output_dir: str,
        filename: str
    ) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """同步下载视频"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            safe_title = self._sanitize_filename(filename) if filename else 'video'
            
            cmd = self._build_cmd(
                url,
                output_dir=str(output_path),
                filename=safe_title,
                merge=True
            )
            
            print(f"开始下载视频: {url}")
            print(f"执行命令: {' '.join(cmd)}")
            
            # 使用 Popen 实时输出进度
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 实时输出进度
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        # 实时打印输出，不换行避免重复换行
                        print(line.rstrip(), flush=True)
                
                process.wait(timeout=600)
                returncode = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                print("下载视频超时")
                return None, None
            
            if returncode != 0:
                print(f"下载失败，返回码: {returncode}")
                return None, None
            
            video_path = self._find_downloaded_video(output_path, safe_title)
            
            if video_path:
                print(f"视频下载成功: {video_path}")
                return video_path, None
            else:
                print("未找到下载的视频文件")
                return None, None
                
        except subprocess.TimeoutExpired:
            print("下载视频超时")
            return None, None
        except Exception as e:
            print(f"下载视频失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def extract_video_id(self, url: str, video_info: Optional[Dict[str, Any]] = None) -> str:
        """从 URL 或信息中提取 Bilibili 视频 ID"""
        # 尝试从 URL 中提取 BV 号
        bv_match = re.search(r'BV([a-zA-Z0-9]+)', url)
        if bv_match:
            return f"BV{bv_match.group(1)}"
        
        # 尝试从 URL 中提取 av 号
        av_match = re.search(r'av(\d+)', url, re.IGNORECASE)
        if av_match:
            return f"av{av_match.group(1)}"
        
        # 尝试从信息中提取
        if video_info:
            video_id = video_info.get('id') or video_info.get('aid') or video_info.get('bvid')
            if video_id:
                return str(video_id)
        
        # 如果都提取不到，使用 URL 的哈希值
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def _convert_bilibili_info_to_dict(self, info: Dict[str, Any], url: str, video_id: str) -> Dict[str, Any]:
        """将 Bilibili 视频信息转换为统一的字典格式"""
        try:
            streams = info.get('streams', {})
            first_stream = list(streams.values())[0] if streams else {}
            
            raw_info = {
                'title': info.get('title', ''),
                'description': info.get('description', '') or info.get('title', ''),
                'height': first_stream.get('height', 0) if first_stream else 0,
                'width': first_stream.get('width', 0) if first_stream else 0,
                'duration': info.get('duration', ''),
                'thumbnail': info.get('thumbnail', ''),
                'uploader_id': info.get('uploader_id', ''),
                'uploader': info.get('uploader', ''),
                'view_count': info.get('view_count', 0),
            }
            
            return self.normalize_video_info(raw_info, url, video_id)
            
        except Exception as e:
            print(f"转换 Bilibili 视频信息失败: {e}")
            return {
                'id': video_id,
                'url': url,
                'platform': 'bilibili',
                'title': info.get('title', ''),
            }
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return 'bilibili'
    
    def supports_url(self, url: str) -> bool:
        """检查是否支持该URL"""
        return 'bilibili.com' in url.lower()
    
    def _build_cmd(
        self,
        url: str,
        output_dir: Optional[str] = None,
        format_id: Optional[str] = None,
        filename: Optional[str] = None,
        merge: bool = True,
        info_only: bool = False,
        json_output: bool = False
    ) -> list:
        """构建 you-get 命令"""
        if isinstance(self.you_get_cmd, str):
            cmd = [self.you_get_cmd]
        else:
            cmd = list(self.you_get_cmd)
        
        if json_output:
            cmd.append('--json')
        
        if info_only:
            cmd.append('--info')
        
        if self.cookies_file:
            cmd.extend(['--cookies', str(self.cookies_file)])
        
        if output_dir:
            cmd.extend(['-o', output_dir])
        
        if format_id:
            cmd.extend(['--format', format_id])
        
        if not merge:
            cmd.append('--no-merge')

        if filename:
            cmd.extend(['-O', filename])

        cmd.append(url)
        
        return cmd
    
    def _find_downloaded_video(self, output_dir: Path, title: str) -> Optional[str]:
        """查找已下载的视频文件"""
        try:
            video_extensions = ['.mp4', '.flv', '.webm', '.mkv', '.mov', '.avi']
            
            # 首先尝试精确匹配标题
            for ext in video_extensions:
                video_file = output_dir / f"{title}{ext}"
                if video_file.exists():
                    return str(video_file.resolve())
            
            return None
            
        except Exception as e:
            print(f"查找下载的视频文件失败: {e}")
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip(' .')
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def __del__(self):
        """清理临时文件"""
        if self._temp_cookies_file and self.cookies_file and os.path.exists(self.cookies_file):
            try:
                os.remove(self.cookies_file)
            except Exception:
                pass

