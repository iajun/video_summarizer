"""
AI Service Module - FastAPI服务化
提供视频AI总结的HTTP API接口
"""

import sys
from pathlib import Path

# 将 tiktok_downloader submodule 添加到 Python 路径
# 这样 submodule 内部的 from src.xxx 导入才能正常工作
BASE_DIR = Path(__file__).parent.parent
TIKTOK_DOWNLOADER_PATH = BASE_DIR / "tiktok_downloader"
if TIKTOK_DOWNLOADER_PATH.exists() and str(TIKTOK_DOWNLOADER_PATH) not in sys.path:
    sys.path.insert(0, str(TIKTOK_DOWNLOADER_PATH))

from .utils import VideoProcessor, AudioExtractor, S3Client
from .services import TranscriptionService, AISummarizer
from .api import app
from .workers import TaskWorker, get_worker, background_task_processor
from .models import Task, TaskStatus, Video
from .db import get_db, get_db_session, init_db

__all__ = [
    'VideoProcessor',
    'AudioExtractor',
    'TranscriptionService',
    'AISummarizer',
    'app',
    'TaskWorker',
    'get_worker',
    'background_task_processor',
    'Task',
    'TaskStatus',
    'Video',
    'S3Client',
    'get_db',
    'get_db_session',
    'init_db',
]
