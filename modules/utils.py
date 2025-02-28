"""
工具函数模块，提供各种辅助功能
"""
import os
import time
import uuid
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from config import logger, SCREENSHOTS_DIR, FILE_RETENTION_DAYS, TEMP_DIR, UPLOADS_DIR

def generate_unique_filename(prefix='img', ext='jpg'):
    """
    生成唯一文件名
    
    Args:
        prefix: 文件名前缀
        ext: 文件扩展名
        
    Returns:
        唯一文件名
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{unique_id}.{ext}"

def save_image(image, prefix='detected'):
    """
    保存图像
    
    Args:
        image: OpenCV格式的图像
        prefix: 文件名前缀
        
    Returns:
        保存的文件路径
    """
    try:
        if image is None:
            logger.error("保存图像失败: 图像为空")
            return None
            
        filename = generate_unique_filename(prefix)
        filepath = SCREENSHOTS_DIR / filename
        
        # OpenCV的BGR格式转换为RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 使用PIL保存图像
        Image.fromarray(rgb_image).save(filepath)
        
        logger.info(f"图像已保存: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"保存图像失败: {str(e)}")
        return None

def load_image(image_path):
    """
    加载图像
    
    Args:
        image_path: 图像路径
        
    Returns:
        加载的图像，OpenCV格式
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(image_path):
            logger.error(f"图像加载失败: 文件不存在 {image_path}")
            return None
            
        # 使用OpenCV加载图像
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"图像加载失败: 无法读取 {image_path}")
            return None
            
        return image
    except Exception as e:
        logger.error(f"图像加载失败: {str(e)}")
        return None

def resize_image(image, width=None, height=None):
    """
    调整图像大小
    
    Args:
        image: OpenCV格式的图像
        width: 目标宽度，如果为None则按比例缩放
        height: 目标高度，如果为None则按比例缩放
        
    Returns:
        调整大小后的图像
    """
    if image is None:
        return None
        
    h, w = image.shape[:2]
    
    if width is None and height is None:
        return image
        
    if width is None:
        aspect_ratio = height / float(h)
        new_width = int(w * aspect_ratio)
        new_size = (new_width, height)
    elif height is None:
        aspect_ratio = width / float(w)
        new_height = int(h * aspect_ratio)
        new_size = (width, new_height)
    else:
        new_size = (width, height)
        
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

def get_video_properties(video_path):
    """
    获取视频属性
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        包含视频属性的字典，如果出错则返回None
    """
    try:
        if not os.path.exists(video_path):
            logger.error(f"视频不存在: {video_path}")
            return None
            
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"无法打开视频: {video_path}")
            return None
            
        # 获取视频属性
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        properties = {
            'width': width,
            'height': height,
            'fps': fps,
            'frame_count': frame_count,
            'duration': duration  # 视频时长（秒）
        }
        
        return properties
    except Exception as e:
        logger.error(f"获取视频属性失败: {str(e)}")
        return None

def format_time(seconds):
    """
    将秒数格式化为时:分:秒格式
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串
    """
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def clean_old_files(directory, days=None):
    """
    清理指定目录中的旧文件
    
    Args:
        directory: 要清理的目录路径
        days: 文件保留天数，None表示使用配置文件中的值
        
    Returns:
        清理的文件数量
    """
    if days is None:
        days = FILE_RETENTION_DAYS
        
    # 如果设置为0，表示不自动清理
    if days <= 0:
        return 0
        
    try:
        if not os.path.exists(directory):
            logger.warning(f"清理目录不存在: {directory}")
            return 0
            
        # 计算截止日期
        cutoff_date = datetime.now() - timedelta(days=days)
        count = 0
        
        # 遍历目录中的所有文件
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            # 只处理文件，不处理目录
            if os.path.isfile(item_path):
                # 获取文件的修改时间
                mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                
                # 如果文件修改时间早于截止日期，删除它
                if mtime < cutoff_date:
                    os.remove(item_path)
                    count += 1
                    
        if count > 0:
            logger.info(f"已清理 {count} 个过期文件（{days}天）从 {directory}")
            
        return count
    except Exception as e:
        logger.error(f"清理文件失败: {str(e)}")
        return 0

def clean_all_temp_directories():
    """
    清理所有临时文件夹
    
    Returns:
        清理的文件总数
    """
    total = 0
    
    # 清理各个目录
    total += clean_old_files(SCREENSHOTS_DIR)
    total += clean_old_files(TEMP_DIR, days=1)  # 临时文件只保留1天
    total += clean_old_files(UPLOADS_DIR)
    
    return total 