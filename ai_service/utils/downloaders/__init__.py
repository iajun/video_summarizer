"""
视频下载器模块
支持多平台视频下载，可扩展架构
"""
from .base import BaseDownloader, DownloadResult
from .factory import DownloaderFactory, get_downloader

__all__ = [
    'BaseDownloader',
    'DownloadResult',
    'DownloaderFactory',
    'get_downloader',
]

