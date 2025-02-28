"""
配置管理模块，负责加载和管理应用配置
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 基础路径
BASE_DIR = Path(__file__).resolve().parent

# 人脸匹配阈值
FACE_TOLERANCE = float(os.getenv('FACE_TOLERANCE', 0.5))

# 检测频率
DETECTION_FREQUENCY = int(os.getenv('DETECTION_FREQUENCY', 30))

# 输出目录
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
OUTPUT_PATH = BASE_DIR / OUTPUT_DIR
SCREENSHOTS_DIR = OUTPUT_PATH / 'screenshots'
LOGS_DIR = OUTPUT_PATH / 'logs'
TEMP_DIR = OUTPUT_PATH / 'temp'
UPLOADS_DIR = OUTPUT_PATH / 'uploads'

# 确保目录存在
OUTPUT_PATH.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# 文件保留天数（0表示不自动清理）
FILE_RETENTION_DAYS = int(os.getenv('FILE_RETENTION_DAYS', 7))

# 检测结果最小时间间隔（秒）
MIN_DETECTION_INTERVAL = float(os.getenv('MIN_DETECTION_INTERVAL', 2.0))

# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = LOGS_DIR / 'app.log'

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# 获取logger
logger = logging.getLogger('face_monitor') 