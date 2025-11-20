"""
音频提取模块
负责从视频中提取音频文件
使用S3存储，video_id作为文件名
"""

import os
import subprocess
import tempfile
import asyncio
from pathlib import Path
from typing import Optional
from .s3_client import S3Client  # 同一目录，不需要修改
from .task_queue import run_io_blocking, run_io_bound


class AudioExtractor:
    """音频提取器"""
    
    def __init__(self):
        self.s3_client = S3Client()
    
    def check_file_exists(self, file_path: str) -> bool:
        """检查文件是否存在且不为空"""
        try:
            return os.path.exists(file_path) and os.path.getsize(file_path) > 0
        except:
            return False
    
    def extract_audio(self, video_path: str, video_id: str, force_extract: bool = False) -> Optional[str]:
        """
        从视频中提取音频
        
        Args:
            video_path: 视频文件本地路径
            video_id: 视频ID，用作文件名
            force_extract: 是否强制重新提取
            
        Returns:
            音频文件本地路径
        """
        try:
            # 首先检查视频是否包含音频流
            has_audio = self._has_audio_stream(video_path)
            if not has_audio:
                print(f"视频文件不包含音频流: {video_path}")
                return None
            
            # 本地临时音频文件
            temp_dir = Path(tempfile.gettempdir()) / "ai_service_downloads"
            temp_dir.mkdir(exist_ok=True)
            audio_path = temp_dir / f"{video_id}_audio.wav"
            
            print(f"正在提取音频: {video_path} -> {audio_path}")
            
            # 使用ffmpeg提取音频
            cmd = [
                "ffmpeg", "-i", video_path, 
                "-vn", "-acodec", "pcm_s16le", 
                "-ar", "16000", "-ac", "1", 
                "-y", str(audio_path)
            ]
            
            # 为 ffmpeg 添加超时，防止卡死
            result = run_io_blocking(subprocess.run, cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                print(f"音频提取失败: {result.stderr}")
                return None
            
            print(f"音频提取成功: {audio_path}")
            
            return str(audio_path)
            
        except Exception as e:
            print(f"音频提取失败: {str(e)}")
            return None
    
    def _has_audio_stream(self, video_path: str) -> bool:
        """
        检查视频文件是否包含音频流
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            如果包含音频流返回 True，否则返回 False
        """
        try:
            # 使用 ffprobe 检查视频流信息
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = run_io_blocking(subprocess.run, cmd, capture_output=True, text=True, timeout=30)
            # 如果找到音频流，ffprobe 会输出 "audio"
            return result.returncode == 0 and "audio" in result.stdout.lower()
        except Exception as e:
            print(f"检查音频流失败: {str(e)}")
            # 如果检查失败，假设有音频流，让后续的提取过程来处理
            return True
    
    async def _has_audio_stream_async(self, video_path: str) -> bool:
        """异步版本：检查视频文件是否包含音频流"""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = await run_io_bound(subprocess.run, cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0 and "audio" in result.stdout.lower()
        except Exception as e:
            print(f"检查音频流失败: {str(e)}")
            return True

    async def extract_audio_async(self, video_path: str, video_id: str, force_extract: bool = False) -> Optional[str]:
        """异步版本：在共享 IO 线程池中执行阻塞步骤，避免阻塞事件循环。"""
        try:
            # 首先检查视频是否包含音频流
            has_audio = await self._has_audio_stream_async(video_path)
            if not has_audio:
                print(f"视频文件不包含音频流: {video_path}")
                return None
            
            temp_dir = Path(tempfile.gettempdir()) / "ai_service_downloads"
            temp_dir.mkdir(exist_ok=True)
            audio_path = temp_dir / f"{video_id}_audio.wav"
            
            print(f"正在提取音频: {video_path} -> {audio_path}")
            cmd = [
                "ffmpeg", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1",
                "-y", str(audio_path)
            ]
            # 在线程池中运行阻塞的 subprocess.run
            # 为 ffmpeg 添加超时，防止卡死
            result = await run_io_bound(subprocess.run, cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                print(f"音频提取失败: {result.stderr}")
                return None
            
            print(f"音频提取成功: {audio_path}")
            return str(audio_path)
        except Exception as e:
            print(f"音频提取失败: {str(e)}")
            return None



