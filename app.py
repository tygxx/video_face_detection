"""
人脸监测系统主应用程序
"""
import os
import json
import uuid
import time
import threading
import base64
from datetime import datetime
from pathlib import Path

import cv2
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, send_from_directory

from config import logger, FACE_TOLERANCE, SCREENSHOTS_DIR, MIN_DETECTION_INTERVAL, TEMP_DIR
from modules.face_detector import FaceDetector
from modules.video_processor import VideoProcessor
from modules.utils import save_image, clean_old_files, clean_all_temp_directories

# 初始化Flask应用
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 600 * 1024 * 1024  # 限制上传文件大小（500MB）
app.config['UPLOAD_FOLDER'] = 'output/uploads'
app.config['TEMP_FOLDER'] = 'output/temp'

# 确保目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

# 存储当前任务信息
tasks = {}

# 应用启动时执行一次清理
clean_all_temp_directories()

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg'},
    'video': {'mp4', 'avi', 'mov', 'mkv'}
}

def allowed_file(filename, file_type):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS.get(file_type, set())

def get_file_path(file, folder, prefix=''):
    """处理上传的文件并返回保存路径"""
    if file and file.filename:
        # 生成安全的文件名
        original_filename = file.filename
        extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        
        if prefix:
            filename = f"{prefix}_{timestamp}_{unique_id}.{extension}"
        else:
            filename = f"{timestamp}_{unique_id}.{extension}"
            
        filepath = os.path.join(folder, filename)
        file.save(filepath)
        return filepath
    return None

def get_task_status(task_id):
    """获取任务状态"""
    task = tasks.get(task_id)
    if not task:
        return None
    
    # 从任务中获取进度信息
    processor = task.get('processor')
    if not processor:
        return {
            'progress': 0,
            'completed': False,
            'error': '任务未初始化'
        }
    
    # 获取进度
    progress_info = processor.get_progress_info()
    
    # 返回状态信息
    return {
        'progress': progress_info['progress'],
        'current_frame': progress_info['current_frame'],
        'total_frames': progress_info['total_frames'],
        'processed_frames': progress_info['processed_frames'],
        'matched_frames': progress_info['matched_frames'],
        'is_processing': progress_info['is_processing'],
        'completed': not progress_info['is_processing'],
        'total_matches': len(processor.get_detection_results())
    }

def process_video_task(task_id, video_path, face_path, tolerance):
    """在后台处理视频的任务"""
    try:
        task = tasks.get(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return
        
        # 初始化人脸检测器
        face_detector = FaceDetector()
        face_detector.tolerance = float(tolerance)
        
        # 加载参考人脸
        if not face_detector.load_reference_face(face_path):
            task['error'] = '无法加载参考人脸'
            return
        
        # 初始化视频处理器
        processor = VideoProcessor(face_detector)
        # 设置最小检测时间间隔
        processor.min_time_interval = MIN_DETECTION_INTERVAL
        task['processor'] = processor
        
        # 加载视频
        if not processor.load_video(video_path):
            task['error'] = '无法加载视频'
            return
        
        # 更新实时预览画面的回调函数
        def progress_callback(frame_index, total_frames, progress, current_frame):
            # 保存当前帧为预览图像
            if current_frame is not None and frame_index % 10 == 0:  # 每10帧更新一次预览
                preview_path = os.path.join(app.config['TEMP_FOLDER'], f"preview_{task_id}.jpg")
                cv2.imwrite(preview_path, current_frame)
                task['preview_image'] = preview_path
            
            # 继续处理
            return True
        
        # 处理视频
        results = processor.process_video(progress_callback)
        
        # 处理完成，更新任务信息
        task['results'] = results
        task['completed'] = True
        
        logger.info(f"任务完成: {task_id}, 检测到 {len(results)} 个匹配")
        
        # 每次任务完成后清理一下临时文件
        clean_old_files(TEMP_DIR, days=1)
    except Exception as e:
        logger.error(f"处理视频任务异常: {str(e)}")
        task['error'] = str(e)
    finally:
        task['is_processing'] = False

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """处理文件上传"""
    # 检查是否有文件
    if 'referFace' not in request.files or 'videoFile' not in request.files:
        flash('请上传人脸照片和视频文件', 'danger')
        return jsonify({'success': False, 'error': '请上传人脸照片和视频文件'})
    
    refer_face = request.files['referFace']
    video_file = request.files['videoFile']
    
    # 检查文件名
    if refer_face.filename == '' or video_file.filename == '':
        flash('未选择文件', 'danger')
        return jsonify({'success': False, 'error': '未选择文件'})
    
    # 检查文件类型
    if not allowed_file(refer_face.filename, 'image'):
        flash('人脸照片格式不支持，请上传 PNG, JPG 或 JPEG 格式', 'danger')
        return jsonify({'success': False, 'error': '人脸照片格式不支持，请上传 PNG, JPG 或 JPEG 格式'})
    
    if not allowed_file(video_file.filename, 'video'):
        flash('视频格式不支持，请上传 MP4, AVI, MOV 或 MKV 格式', 'danger')
        return jsonify({'success': False, 'error': '视频格式不支持，请上传 MP4, AVI, MOV 或 MKV 格式'})
    
    # 获取匹配阈值
    tolerance = request.form.get('tolerance', FACE_TOLERANCE)
    
    # 保存文件
    face_path = get_file_path(refer_face, app.config['UPLOAD_FOLDER'], 'face')
    video_path = get_file_path(video_file, app.config['UPLOAD_FOLDER'], 'video')
    
    if not face_path or not video_path:
        flash('文件保存失败', 'danger')
        return jsonify({'success': False, 'error': '文件保存失败'})
    
    # 创建任务ID
    task_id = str(uuid.uuid4())
    
    # 初始化任务
    tasks[task_id] = {
        'id': task_id,
        'face_path': face_path,
        'video_path': video_path,
        'tolerance': tolerance,
        'timestamp': datetime.now().isoformat(),
        'is_processing': True,
        'processor': None,
        'preview_image': None,
        'error': None,
        'results': [],
        'completed': False
    }
    
    # 启动后台处理线程
    thread = threading.Thread(
        target=process_video_task,
        args=(task_id, video_path, face_path, tolerance)
    )
    thread.daemon = True
    thread.start()
    
    flash('文件上传成功，开始处理', 'success')
    return jsonify({
        'success': True,
        'task_id': task_id
    })

@app.route('/progress/<task_id>')
def progress(task_id):
    """获取处理进度"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    # 获取任务状态
    status = get_task_status(task_id)
    if not status:
        return jsonify({'success': False, 'error': '无法获取任务状态'})
    
    # 检查是否有错误
    if task.get('error'):
        return jsonify({
            'success': False,
            'error': task['error'],
            'progress': 0,
            'completed': True
        })
    
    # 获取最新结果
    processor = task.get('processor')
    all_results = processor.get_detection_results() if processor else []
    
    # 计算新增结果（前端可能已经显示了部分结果）
    current_count = int(request.args.get('current_count', 0))
    
    # 确保current_count不超过结果总数
    current_count = min(current_count, len(all_results))
    
    # 获取新结果
    new_results = all_results[current_count:] if current_count < len(all_results) else []
    
    # 转换结果为前端格式
    formatted_results = []
    for i, result in enumerate(new_results, start=current_count + 1):
        # 获取截图的相对URL
        screenshot_path = Path(result['screenshot_path'])
        screenshot_filename = screenshot_path.name
        screenshot_url = url_for('get_screenshot', filename=screenshot_filename)
        
        formatted_results.append({
            'index': i,
            'frame_index': result['frame_index'],
            'timestamp': result['timestamp'],
            'formatted_time': result['formatted_time'],
            'matches_count': result['matches_count'],
            'screenshot_url': screenshot_url
        })
    
    # 获取预览图像的URL（如果有）
    preview_url = None
    if task.get('preview_image'):
        preview_path = Path(task['preview_image'])
        preview_filename = preview_path.name
        preview_url = url_for('get_preview', filename=preview_filename)
    
    return jsonify({
        'success': True,
        'progress': status['progress'],
        'current_frame': status['current_frame'],
        'total_frames': status['total_frames'],
        'processed_frames': status['processed_frames'],
        'matched_frames': status['matched_frames'],
        'total_matches': len(all_results),
        'new_results': formatted_results,
        'preview_image': preview_url,
        'completed': status['completed']
    })

@app.route('/stop', methods=['POST'])
def stop_processing():
    """停止当前处理任务"""
    task_id = request.form.get('task_id')
    
    # 如果没有指定任务ID，尝试停止所有任务
    if not task_id:
        for task in tasks.values():
            processor = task.get('processor')
            if processor and task.get('is_processing', False):
                processor.stop_processing()
                task['is_processing'] = False
        return jsonify({'success': True, 'message': '所有任务已停止'})
    
    # 停止指定任务
    task = tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    processor = task.get('processor')
    if processor and task.get('is_processing', False):
        processor.stop_processing()
        task['is_processing'] = False
        return jsonify({'success': True, 'message': '任务已停止'})
    
    return jsonify({'success': False, 'error': '任务已完成或未开始'})

@app.route('/screenshots/<filename>')
def get_screenshot(filename):
    """获取截图文件"""
    return send_from_directory(SCREENSHOTS_DIR, filename)

@app.route('/temp/<filename>')
def get_preview(filename):
    """获取预览图像"""
    return send_from_directory(app.config['TEMP_FOLDER'], filename)

@app.route('/results/<task_id>')
def get_results(task_id):
    """获取任务结果"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    # 如果任务还在处理中
    if task.get('is_processing', False):
        return jsonify({
            'success': True,
            'completed': False,
            'message': '任务处理中'
        })
    
    # 如果有错误
    if task.get('error'):
        return jsonify({
            'success': False,
            'error': task['error'],
            'completed': True
        })
    
    # 获取结果
    processor = task.get('processor')
    results = processor.get_detection_results() if processor else []
    
    # 转换结果为前端格式
    formatted_results = []
    for i, result in enumerate(results, start=1):
        # 获取截图的相对URL
        screenshot_path = Path(result['screenshot_path'])
        screenshot_filename = screenshot_path.name
        screenshot_url = url_for('get_screenshot', filename=screenshot_filename)
        
        formatted_results.append({
            'index': i,
            'frame_index': result['frame_index'],
            'timestamp': result['timestamp'],
            'formatted_time': result['formatted_time'],
            'matches_count': result['matches_count'],
            'screenshot_url': screenshot_url
        })
    
    return jsonify({
        'success': True,
        'completed': True,
        'results': formatted_results,
        'total_matches': len(results)
    })

@app.route('/clean_files', methods=['POST'])
def clean_files():
    """手动清理文件"""
    try:
        # 强制清理所有临时目录
        total = clean_all_temp_directories()
        
        return jsonify({
            'success': True,
            'message': f'成功清理 {total} 个文件',
            'deleted_count': total
        })
    except Exception as e:
        logger.error(f"手动清理文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'清理文件失败: {str(e)}'
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 