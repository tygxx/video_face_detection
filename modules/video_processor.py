"""
视频处理模块，负责视频解析和处理
"""
import os
import cv2
import time
from datetime import timedelta

from config import logger, DETECTION_FREQUENCY
from modules.utils import save_image, get_video_properties, format_time


class VideoProcessor:
    """视频处理器类，提供视频分析和人脸检测功能"""
    
    def __init__(self, face_detector, detection_frequency=None):
        """
        初始化视频处理器
        
        Args:
            face_detector: 人脸检测器对象
            detection_frequency: 检测频率，每多少帧检测一次
        """
        self.face_detector = face_detector
        self.detection_frequency = detection_frequency or DETECTION_FREQUENCY
        self.current_video_path = None
        self.video_capture = None
        self.frame_count = 0
        self.processed_frames = 0
        self.matched_frames = 0
        self.current_frame_index = 0
        self.video_fps = 0
        self.detection_results = []
        self.is_processing = False
        # 添加最小时间间隔属性（秒），避免短时间内重复记录同一人脸
        self.min_time_interval = 2.0
        # 上次检测到人脸的时间戳
        self.last_detection_timestamp = -self.min_time_interval
        
    def load_video(self, video_path):
        """
        加载视频文件
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            bool: 是否成功加载
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"视频文件不存在: {video_path}")
                return False
                
            # 关闭之前的视频
            self.close_video()
            
            # 获取视频属性
            properties = get_video_properties(video_path)
            if not properties:
                return False
                
            # 打开新视频
            self.video_capture = cv2.VideoCapture(video_path)
            if not self.video_capture.isOpened():
                logger.error(f"无法打开视频: {video_path}")
                return False
                
            self.current_video_path = video_path
            self.frame_count = properties['frame_count']
            self.video_fps = properties['fps']
            self.current_frame_index = 0
            self.processed_frames = 0
            self.matched_frames = 0
            self.detection_results = []
            # 重置最后检测时间戳
            self.last_detection_timestamp = -self.min_time_interval
            
            logger.info(f"成功加载视频: {video_path}, 总帧数: {self.frame_count}, FPS: {self.video_fps}")
            return True
        except Exception as e:
            logger.error(f"加载视频失败: {str(e)}")
            return False
    
    def close_video(self):
        """关闭当前视频"""
        if self.video_capture and self.video_capture.isOpened():
            self.video_capture.release()
            self.video_capture = None
            self.current_video_path = None
    
    def read_frame(self):
        """
        读取下一帧
        
        Returns:
            tuple: (frame, frame_index, timestamp)
        """
        if not self.video_capture or not self.video_capture.isOpened():
            logger.error("读取帧失败: 未加载视频")
            return None, -1, 0
            
        # 读取帧
        ret, frame = self.video_capture.read()
        
        if not ret:
            return None, -1, 0
            
        frame_index = self.current_frame_index
        self.current_frame_index += 1
        
        # 计算时间戳（秒）
        timestamp = frame_index / self.video_fps if self.video_fps > 0 else 0
        
        return frame, frame_index, timestamp
    
    def process_video(self, callback=None):
        """
        处理整个视频，检测匹配的人脸
        
        Args:
            callback: 回调函数，用于更新进度等
            
        Returns:
            list: 检测结果列表
        """
        if not self.video_capture or not self.video_capture.isOpened():
            logger.error("处理视频失败: 未加载视频")
            return []
            
        if not self.face_detector:
            logger.error("处理视频失败: 未配置人脸检测器")
            return []
            
        try:
            self.is_processing = True
            self.detection_results = []
            self.processed_frames = 0
            self.matched_frames = 0
            
            logger.info(f"开始处理视频: {self.current_video_path}")
            
            # 重置到第一帧
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame_index = 0
            
            start_time = time.time()
            
            while self.is_processing:
                # 读取帧
                frame, frame_index, timestamp = self.read_frame()
                
                if frame is None:
                    # 视频结束
                    break
                    
                # 计算进度
                progress = frame_index / self.frame_count if self.frame_count > 0 else 0
                
                # 只处理符合检测频率的帧
                if frame_index % self.detection_frequency == 0:
                    # 处理帧
                    processed_frame, matches, has_matches = self.face_detector.process_frame(frame)
                    self.processed_frames += 1
                    
                    # 如果检测到匹配的人脸，并且与上次检测时间间隔足够
                    if has_matches and (timestamp - self.last_detection_timestamp >= self.min_time_interval):
                        self.matched_frames += 1
                        self.last_detection_timestamp = timestamp
                        
                        # 格式化时间戳
                        formatted_time = format_time(timestamp)
                        
                        # 保存截图
                        screenshot_path = save_image(processed_frame, prefix="detected")
                        
                        # 记录检测结果
                        result = {
                            'frame_index': frame_index,
                            'timestamp': timestamp,
                            'formatted_time': formatted_time,
                            'screenshot_path': screenshot_path,
                            'matches_count': len(matches)
                        }
                        
                        self.detection_results.append(result)
                        
                        logger.info(f"检测到匹配人脸 - 帧: {frame_index}, 时间: {formatted_time}, 匹配数: {len(matches)}")
                
                # 调用回调函数
                if callback:
                    should_continue = callback(frame_index, self.frame_count, progress, processed_frame if has_matches else frame)
                    if should_continue is False:
                        self.is_processing = False
                        logger.info("用户取消处理")
                        break
            
            # 计算处理时间
            elapsed_time = time.time() - start_time
            
            logger.info(f"视频处理完成 - 总帧数: {self.frame_count}, 处理帧数: {self.processed_frames}, "
                        f"匹配帧数: {self.matched_frames}, 耗时: {elapsed_time:.2f}秒")
            
            return self.detection_results
        except Exception as e:
            logger.error(f"处理视频异常: {str(e)}")
            return []
        finally:
            self.is_processing = False
    
    def stop_processing(self):
        """停止视频处理"""
        self.is_processing = False
        
    def get_detection_results(self):
        """
        获取检测结果
        
        Returns:
            list: 检测结果列表
        """
        return self.detection_results
    
    def get_progress_info(self):
        """
        获取处理进度信息
        
        Returns:
            dict: 进度信息
        """
        progress = self.current_frame_index / self.frame_count if self.frame_count > 0 else 0
        
        return {
            'current_frame': self.current_frame_index,
            'total_frames': self.frame_count,
            'processed_frames': self.processed_frames,
            'matched_frames': self.matched_frames,
            'progress': progress,
            'is_processing': self.is_processing
        } 