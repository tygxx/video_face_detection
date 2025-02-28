# 人脸监测系统

这是一个基于Python的本地视频人脸检测系统，可以在本地视频中查找特定人物的出现，并进行记录。

## 功能特点

- 解析本地视频文件
- 根据提供的人脸照片在视频中查找匹配人脸
- 检测到匹配人脸时，记录日志并保存截图
- 提供Web界面，方便上传视频和人脸照片
- 支持配置检测参数

## 安装

1. 克隆仓库到本地
2. 创建虚拟环境

```bash
conda create -n face_detection python=3.10
conda activate face_detection
```

3. 安装依赖:

```bash
pip install -r requirements.txt
```

注意：face_recognition库依赖于dlib，可能需要额外的安装步骤：

- Windows用户：请确保安装了Visual Studio和CMake
- Linux用户：安装必要的开发库 `sudo apt-get install build-essential cmake`
- Mac用户：`brew install cmake`

## 使用方法

1. 启动应用：

```bash
python app.py
```

2. 在浏览器中访问 `http://localhost:5000`
3. 上传要检测的人脸照片
4. 选择本地视频文件
5. 点击"开始分析"按钮
6. 检测结果会显示在界面上，截图会保存在`output/screenshots`目录下

## 配置

可以在`.env`文件中修改配置参数：

```
# 人脸匹配阈值，越小越严格，范围建议0.4-0.6
FACE_TOLERANCE=0.5

# 检测频率（每隔多少帧检测一次）
DETECTION_FREQUENCY=30

# 输出目录
OUTPUT_DIR=output
```

## 项目结构

```
.
├── app.py                  # 主应用入口
├── config.py               # 配置管理
├── requirements.txt        # 项目依赖
├── .env                    # 环境变量配置
├── static/                 # 静态资源
│   ├── css/
│   ├── js/
│   └── img/
├── templates/              # HTML模板
├── output/                 # 输出文件夹
│   ├── logs/               # 日志文件
│   └── screenshots/        # 截图保存
└── modules/                # 功能模块
    ├── face_detector.py    # 人脸检测模块
    ├── video_processor.py  # 视频处理模块
    └── utils.py            # 工具函数
```

## 调试

如果遇到问题，请检查日志文件：`output/logs/app.log` 