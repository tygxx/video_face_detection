// 页面加载完成后执行
$(document).ready(function() {
    // 更新阈值显示
    $('#tolerance').on('input', function() {
        $('#toleranceValue').text($(this).val());
    });

    // 文件上传监听
    $('#referFace').on('change', function() {
        const fileName = $(this).val().split('\\').pop();
        if (fileName) {
            $('#referFaceStatus').text(fileName);
        } else {
            $('#referFaceStatus').text('未上传');
        }
    });

    $('#videoFile').on('change', function() {
        const fileName = $(this).val().split('\\').pop();
        if (fileName) {
            $('#videoStatus').text(fileName);
        } else {
            $('#videoStatus').text('未上传');
        }
    });

    // 表单提交处理
    $('#uploadForm').on('submit', function(e) {
        e.preventDefault();
        
        // 显示进度条和停止按钮
        $('#progressContainer').removeClass('d-none');
        $('#stopProcessing').removeClass('d-none');
        $('#processStatus').text('处理中...');
        
        // 创建FormData对象
        const formData = new FormData(this);
        
        // 开始处理
        startProcessing(formData);
    });
    
    // 停止处理按钮
    $('#stopProcessing').on('click', function() {
        stopProcessing();
    });
    
    // 图片预览点击事件委托（动态生成的元素）
    $(document).on('click', '.thumbnail', function() {
        const imgSrc = $(this).attr('src');
        $('#modalImage').attr('src', imgSrc);
        const modal = new bootstrap.Modal(document.getElementById('imageModal'));
        modal.show();
    });
    
    // 清理文件按钮
    $('#cleanFiles').on('click', function() {
        cleanFiles();
    });
});

// 全局变量，用于跟踪已显示的结果数量
let displayedResultsCount = 0;

// 开始处理视频
function startProcessing(formData) {
    // 重置界面
    $('#resultsBody').empty();
    $('#resultsCard').addClass('d-none');
    $('#noResults').addClass('d-none');
    $('#previewCard').addClass('d-none');
    
    // 重置已显示的结果计数
    displayedResultsCount = 0;
    
    // AJAX提交文件
    $.ajax({
        url: '/upload',
        type: 'POST',
        data: formData,
        contentType: false,
        processData: false,
        success: function(response) {
            if (response.success) {
                // 显示预览卡片
                $('#previewCard').removeClass('d-none');
                
                // 设置任务ID
                const taskId = response.task_id;
                
                // 开始轮询进度
                pollProgress(taskId);
            } else {
                handleError(response.error);
            }
        },
        error: function(xhr, status, error) {
            handleError('上传失败: ' + error);
        }
    });
}

// 轮询处理进度
function pollProgress(taskId) {
    const progressInterval = setInterval(function() {
        $.ajax({
            url: '/progress/' + taskId + '?current_count=' + displayedResultsCount,
            type: 'GET',
            success: function(response) {
                // 更新进度条
                const progress = response.progress * 100;
                $('#progressBar').css('width', progress + '%');
                
                // 更新状态信息
                $('#processStatus').text('处理中 - ' + Math.round(progress) + '%');
                
                // 如果有预览图像
                if (response.preview_image) {
                    $('#previewImage').attr('src', response.preview_image + '?' + new Date().getTime());
                }
                
                // 如果有新的检测结果
                if (response.new_results && response.new_results.length > 0) {
                    // 显示结果卡片
                    $('#resultsCard').removeClass('d-none');
                    
                    // 添加新结果
                    appendResults(response.new_results);
                    
                    // 更新已显示的结果计数
                    displayedResultsCount += response.new_results.length;
                }
                
                // 如果处理完成
                if (response.completed) {
                    clearInterval(progressInterval);
                    processingCompleted(response);
                }
            },
            error: function(xhr, status, error) {
                clearInterval(progressInterval);
                handleError('获取进度失败: ' + error);
            }
        });
    }, 1000);
    
    // 保存定时器ID以便停止
    window.progressInterval = progressInterval;
}

// 添加检测结果到表格
function appendResults(results) {
    // 检查是否有重复结果，通过URL去重
    const existingUrls = [];
    $('#resultsBody tr').each(function() {
        const url = $(this).find('.thumbnail').attr('src');
        existingUrls.push(url);
    });
    
    results.forEach(function(result, index) {
        // 如果结果URL已存在，跳过
        if (existingUrls.includes(result.screenshot_url)) {
            console.log('跳过重复结果:', result.screenshot_url);
            return;
        }
        
        const row = `
            <tr class="fade-in">
                <td>${result.index}</td>
                <td>${result.formatted_time}</td>
                <td>${result.matches_count}</td>
                <td>
                    <img src="${result.screenshot_url}" class="thumbnail" alt="检测到的人脸">
                </td>
                <td>
                    <a href="${result.screenshot_url}" class="btn btn-sm btn-outline-primary" download>
                        <i class="fas fa-download"></i> 下载
                    </a>
                </td>
            </tr>
        `;
        $('#resultsBody').append(row);
        
        // 添加到已存在URL列表，防止后续添加重复
        existingUrls.push(result.screenshot_url);
    });
}

// 处理完成
function processingCompleted(response) {
    // 隐藏进度条和停止按钮
    $('#progressContainer').addClass('d-none');
    $('#stopProcessing').addClass('d-none');
    
    // 更新状态
    $('#processStatus').text('处理完成');
    
    // 如果没有检测结果
    if (response.total_matches === 0) {
        $('#noResults').removeClass('d-none');
    }
    
    // 显示完成消息
    const message = `视频处理完成！总共处理 ${response.processed_frames} 帧，检测到 ${response.total_matches} 处匹配。`;
    showAlert(message, 'success');
}

// 停止处理
function stopProcessing() {
    // 清除轮询定时器
    if (window.progressInterval) {
        clearInterval(window.progressInterval);
    }
    
    // 发送停止请求
    $.ajax({
        url: '/stop',
        type: 'POST',
        success: function(response) {
            // 隐藏进度条和停止按钮
            $('#progressContainer').addClass('d-none');
            $('#stopProcessing').addClass('d-none');
            
            // 更新状态
            $('#processStatus').text('已停止');
            
            // 显示消息
            showAlert('处理已停止', 'warning');
        },
        error: function(xhr, status, error) {
            handleError('停止处理失败: ' + error);
        }
    });
}

// 清理文件
function cleanFiles() {
    // 确认是否要清理
    if (confirm('确定要清理临时文件吗？\n这将删除系统中的过期文件，但不会影响当前处理中的任务。')) {
        // 发送清理请求
        $.ajax({
            url: '/clean_files',
            type: 'POST',
            success: function(response) {
                if (response.success) {
                    showAlert(response.message, 'success');
                } else {
                    showAlert(response.error, 'danger');
                }
            },
            error: function(xhr, status, error) {
                handleError('清理文件失败: ' + error);
            }
        });
    }
}

// 处理错误
function handleError(errorMessage) {
    // 隐藏进度条和停止按钮
    $('#progressContainer').addClass('d-none');
    $('#stopProcessing').addClass('d-none');
    
    // 更新状态
    $('#processStatus').text('出错');
    
    // 显示错误信息
    showAlert(errorMessage, 'danger');
}

// 显示提示信息
function showAlert(message, type) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // 插入到页面顶部
    $(alertHtml).insertAfter('.display-4').addClass('fade-in');
} 