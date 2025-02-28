"""
人脸检测模块，负责人脸识别和匹配相关功能
"""
import os
import cv2
import numpy as np
import face_recognition

from config import logger, FACE_TOLERANCE
from modules.utils import load_image, save_image


class FaceDetector:
    """人脸检测器类，提供人脸检测和匹配功能"""
    
    def __init__(self, reference_face_path=None):
        """
        初始化人脸检测器
        
        Args:
            reference_face_path: 参考人脸图像的路径
        """
        self.reference_face_path = reference_face_path
        self.reference_face_encoding = None
        self.tolerance = FACE_TOLERANCE
        
        # 如果提供了参考人脸，立即加载
        if reference_face_path:
            self.load_reference_face(reference_face_path)
    
    def load_reference_face(self, face_path):
        """
        加载参考人脸图像并提取特征
        
        Args:
            face_path: 参考人脸图像的路径
            
        Returns:
            bool: 是否成功加载
        """
        try:
            if not os.path.exists(face_path):
                logger.error(f"参考人脸图像不存在: {face_path}")
                return False
                
            # 加载图像
            image = load_image(face_path)
            if image is None:
                return False
                
            # 转换为RGB（face_recognition库需要RGB格式）
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 检测人脸位置
            face_locations = face_recognition.face_locations(rgb_image)
            
            if not face_locations:
                logger.error(f"未在参考图像中检测到人脸: {face_path}")
                return False
                
            # 提取人脸特征
            self.reference_face_encoding = face_recognition.face_encodings(rgb_image, face_locations)[0]
            self.reference_face_path = face_path
            
            logger.info(f"成功加载参考人脸: {face_path}")
            return True
        except Exception as e:
            logger.error(f"加载参考人脸失败: {str(e)}")
            return False
            
    def detect_faces(self, image):
        """
        在图像中检测所有人脸
        
        Args:
            image: OpenCV格式的图像
            
        Returns:
            tuple: (face_locations, face_encodings)
        """
        if image is None:
            logger.error("检测人脸失败: 图像为空")
            return [], []
            
        try:
            # 转换为RGB格式
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 检测人脸位置
            face_locations = face_recognition.face_locations(rgb_image)
            
            # 如果没有检测到人脸，返回空列表
            if not face_locations:
                return [], []
                
            # 提取人脸特征
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            return face_locations, face_encodings
        except Exception as e:
            logger.error(f"检测人脸异常: {str(e)}")
            return [], []
    
    def match_faces(self, image):
        """
        在图像中查找与参考人脸匹配的人脸
        
        Args:
            image: OpenCV格式的图像
            
        Returns:
            list: 匹配的人脸位置列表
        """
        if self.reference_face_encoding is None:
            logger.error("匹配人脸失败: 未加载参考人脸")
            return []
            
        if image is None:
            logger.error("匹配人脸失败: 图像为空")
            return []
            
        try:
            # 检测所有人脸
            face_locations, face_encodings = self.detect_faces(image)
            
            if not face_encodings:
                return []
                
            # 匹配人脸
            matches = []
            for i, face_encoding in enumerate(face_encodings):
                # 计算与参考人脸的距离
                distance = face_recognition.face_distance([self.reference_face_encoding], face_encoding)[0]
                
                # 如果距离小于阈值，认为是匹配的
                if distance < self.tolerance:
                    matches.append({
                        'location': face_locations[i],
                        'distance': distance
                    })
            
            return matches
        except Exception as e:
            logger.error(f"匹配人脸异常: {str(e)}")
            return []
    
    def draw_face_rectangles(self, image, face_locations, color=(0, 255, 0), thickness=2):
        """
        在图像上绘制人脸框
        
        Args:
            image: OpenCV格式的图像
            face_locations: 人脸位置列表，每个位置是(top, right, bottom, left)格式
            color: 矩形颜色，BGR格式
            thickness: 线条粗细
            
        Returns:
            标记后的图像
        """
        if image is None or not face_locations:
            return image
            
        # 创建图像的副本
        result = image.copy()
        
        # 绘制每个人脸的矩形
        for location in face_locations:
            if isinstance(location, dict) and 'location' in location:
                top, right, bottom, left = location['location']
                # 如果有距离信息，在框上方显示匹配度
                if 'distance' in location:
                    confidence = 1 - location['distance']
                    cv2.putText(
                        result, 
                        f"{confidence:.2f}", 
                        (left, top - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, 
                        color, 
                        thickness
                    )
            else:
                top, right, bottom, left = location
            
            # 绘制矩形
            cv2.rectangle(result, (left, top), (right, bottom), color, thickness)
        
        return result
    
    def process_frame(self, frame):
        """
        处理视频帧，检测匹配的人脸并标记
        
        Args:
            frame: 视频帧
            
        Returns:
            tuple: (processed_frame, matches, has_matches)
        """
        if self.reference_face_encoding is None:
            logger.warning("处理帧失败: 未加载参考人脸")
            return frame, [], False
            
        if frame is None:
            logger.error("处理帧失败: 帧为空")
            return frame, [], False
            
        try:
            # 匹配人脸
            matches = self.match_faces(frame)
            
            # 如果有匹配的人脸，标记它们
            if matches:
                frame = self.draw_face_rectangles(frame, matches)
                return frame, matches, True
            else:
                return frame, [], False
        except Exception as e:
            logger.error(f"处理帧异常: {str(e)}")
            return frame, [], False 