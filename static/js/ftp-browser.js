// FTP浏览器功能

let currentSiteId = null;
let currentPath = '/';
let selectedItems = [];
let ftpFileData = [];

// 导航历史
let navigationHistory = [];
let historyIndex = -1;

// 视图和排序设置
let viewMode = 'list'; // 'list' 或 'grid'
let sortMode = 'name'; // 'name', 'size', 'date', 'type'
let sortOrder = 'asc'; // 'asc' 或 'desc'

// 双击防抖
let clickTimeout = null;

// HTML转义函数
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';

    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const size = (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1);

    return `${size} ${sizes[i]}`;
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '';

    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString;

        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays === 0) {
            // 今天，显示时间
            return date.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });
        } else if (diffDays < 7) {
            // 一周内，显示几天前
            return `${diffDays}天前`;
        } else {
            // 超过一周，显示日期
            return date.toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        }
    } catch (e) {
        return dateString;
    }
}

// 获取文件图标
function getFileIcon(file) {
    if (file.is_directory) {
        return 'bi-folder-fill';
    }

    const ext = getFileExtension(file.name).toLowerCase();
    const iconMap = {
        'txt': 'bi-file-text',
        'doc': 'bi-file-word',
        'docx': 'bi-file-word',
        'pdf': 'bi-file-pdf',
        'xls': 'bi-file-excel',
        'xlsx': 'bi-file-excel',
        'ppt': 'bi-file-ppt',
        'pptx': 'bi-file-ppt',
        'jpg': 'bi-file-image',
        'jpeg': 'bi-file-image',
        'png': 'bi-file-image',
        'gif': 'bi-file-image',
        'mp3': 'bi-file-music',
        'wav': 'bi-file-music',
        'mp4': 'bi-file-play',
        'avi': 'bi-file-play',
        'zip': 'bi-file-zip',
        'rar': 'bi-file-zip',
        '7z': 'bi-file-zip'
    };

    return iconMap[ext] || 'bi-file-earmark';
}

// 获取文件扩展名
function getFileExtension(filename) {
    const lastDot = filename.lastIndexOf('.');
    return lastDot > 0 ? filename.substring(lastDot + 1) : '';
}

// 获取文件类型描述
function getFileType(filename) {
    const ext = getFileExtension(filename).toLowerCase();
    const typeMap = {
        'txt': '文本文档',
        'doc': 'Word文档',
        'docx': 'Word文档',
        'pdf': 'PDF文档',
        'xls': 'Excel表格',
        'xlsx': 'Excel表格',
        'ppt': 'PowerPoint演示文稿',
        'pptx': 'PowerPoint演示文稿',
        'jpg': 'JPEG图像',
        'jpeg': 'JPEG图像',
        'png': 'PNG图像',
        'gif': 'GIF图像',
        'mp3': 'MP3音频',
        'wav': 'WAV音频',
        'mp4': 'MP4视频',
        'avi': 'AVI视频',
        'zip': 'ZIP压缩文件',
        'rar': 'RAR压缩文件',
        '7z': '7Z压缩文件'
    };

    return typeMap[ext] || (ext ? ext.toUpperCase() + '文件' : '文件');
}

// 更新状态信息
function updateStatusInfo(folderCount, fileCount) {
    const statusInfo = document.getElementById('statusInfo');
    const selectionInfo = document.getElementById('selectionInfo');

    let statusText = '';
    if (folderCount > 0 && fileCount > 0) {
        statusText = `${folderCount} 个文件夹，${fileCount} 个文件`;
    } else if (folderCount > 0) {
        statusText = `${folderCount} 个文件夹`;
    } else if (fileCount > 0) {
        statusText = `${fileCount} 个文件`;
    } else {
        statusText = '空文件夹';
    }

    statusInfo.textContent = statusText;

    // 更新选择信息
    const selectedCount = selectedItems.length;
    if (selectedCount > 0) {
        selectionInfo.textContent = `已选择 ${selectedCount} 项`;
    } else {
        selectionInfo.textContent = '';
    }
}

// 显示FTP浏览器模态框
function showFTPBrowserModal() {
    // 加载站点列表
    loadSitesForBrowser();

    // 重置状态
    currentSiteId = null;
    currentPath = '/';
    selectedItems = [];
    ftpFileData = [];
    navigationHistory = [];
    historyIndex = -1;

    // 重置UI
    document.getElementById('ftpCurrentPath').value = '/';
    document.getElementById('addressBar').value = '/';
    document.getElementById('ftpFileList').innerHTML = `
        <div class="text-center text-muted p-4">
            <i class="bi bi-folder2-open fa-3x mb-3"></i>
            <h6>请选择FTP站点开始浏览</h6>
            <p class="small">选择站点后将显示服务器文件和文件夹</p>
        </div>
    `;

    // 重置任务配置
    document.getElementById('ftpTaskType').value = '';
    document.getElementById('ftpLocalPath').value = '/downloads';
    document.getElementById('taskPriority').value = 'medium';
    document.getElementById('autoStart').checked = true;
    document.getElementById('monitorInterval').value = 300;
    document.getElementById('fileFilter').value = '';
    document.getElementById('monitorConfig').style.display = 'none';

    // 重置按钮状态
    updateNavigationButtons();
    updateCreateTaskButton();

    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('ftpBrowserModal'));
    modal.show();
}

// 加载站点列表到选择框
async function loadSitesForBrowser() {
    try {
        const data = await apiRequest('/sites/api/sites');
        const sites = data.sites;
        const select = document.getElementById('ftpSiteSelect');
        
        // 清空现有选项
        select.innerHTML = '<option value="">请选择站点...</option>';
        
        // 添加站点选项
        sites.forEach(site => {
            const option = document.createElement('option');
            option.value = site.id;

            // 添加连接状态指示
            let statusIcon = '';
            if (site.status === 'connected') {
                statusIcon = '🟢';
            } else if (site.status === 'disconnected') {
                statusIcon = '🔴';
            } else {
                statusIcon = '⚪';
            }

            option.textContent = `${statusIcon} ${site.name} (${site.host}:${site.port})`;
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error('Failed to load sites:', error);
        showToast('error', '加载站点列表失败: ' + error.message);
    }
}

// 加载FTP目录
async function loadFTPDirectory() {
    const siteId = document.getElementById('ftpSiteSelect').value;
    console.log('loadFTPDirectory called, siteId:', siteId, 'currentPath:', currentPath);

    if (!siteId) {
        showToast('warning', '请先选择FTP站点');
        return;
    }

    currentSiteId = siteId;
    
    try {
        showLoadingInFileList();

        console.log('Making API request to browse directory:', {
            siteId: siteId,
            path: currentPath,
            url: `/sites/api/sites/${siteId}/browse`
        });

        const response = await apiRequest(`/sites/api/sites/${siteId}/browse`, {
            method: 'POST',
            body: JSON.stringify({ path: currentPath })
        });

        console.log('API response received:', response);

        ftpFileData = response.files || [];
        console.log('File data processed:', ftpFileData);

        updateFileList(ftpFileData);
        updateBreadcrumb();
        updateNavigationButtons();
        
    } catch (error) {
        console.error('Failed to load FTP directory:', error);
        let errorMessage = '加载目录失败';

        if (error.message.includes('连接失败')) {
            errorMessage = 'FTP连接失败，请检查站点配置';
        } else if (error.message.includes('Authentication failed')) {
            errorMessage = 'FTP认证失败，请检查用户名和密码';
        } else if (error.message.includes('Permission denied')) {
            errorMessage = '权限不足，无法访问该目录';
        } else {
            errorMessage += ': ' + error.message;
        }

        showErrorInFileList(errorMessage);
        showToast('error', errorMessage);
    }
}

// 显示加载状态
function showLoadingInFileList() {
    const fileList = document.getElementById('ftpFileList');
    fileList.innerHTML = `
        <div class="text-center text-muted p-4">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2">正在加载目录...</p>
        </div>
    `;
}

// 显示错误信息
function showErrorInFileList(message) {
    const fileList = document.getElementById('ftpFileList');
    fileList.innerHTML = `
        <div class="text-center text-danger p-4">
            <i class="bi bi-exclamation-triangle fa-2x"></i>
            <p class="mt-2">${message}</p>
            <button class="btn btn-sm btn-outline-primary" onclick="loadFTPDirectory()">
                <i class="bi bi-arrow-clockwise"></i> 重试
            </button>
        </div>
    `;
}

// 更新文件列表
function updateFileList(files) {
    const fileList = document.getElementById('ftpFileList');

    if (files.length === 0) {
        fileList.innerHTML = `
            <div class="text-center text-muted p-4">
                <i class="bi bi-folder2-open fa-3x mb-3"></i>
                <h6>目录为空</h6>
                <p class="small">此文件夹中没有任何项目</p>
            </div>
        `;
        updateStatusInfo(0, 0);
        return;
    }

    // 排序文件
    const sortedFiles = sortFiles(files);

    if (viewMode === 'list') {
        updateListView(sortedFiles);
    } else {
        updateGridView(sortedFiles);
    }

    // 更新状态信息
    const folderCount = sortedFiles.filter(f => f.is_directory).length;
    const fileCount = sortedFiles.filter(f => !f.is_directory).length;
    updateStatusInfo(folderCount, fileCount);
}

// 排序文件
function sortFiles(files) {
    return files.sort((a, b) => {
        // 文件夹总是在文件前面（除非按类型排序）
        if (sortMode !== 'type') {
            if (a.is_directory && !b.is_directory) return -1;
            if (!a.is_directory && b.is_directory) return 1;
        }

        let comparison = 0;

        switch (sortMode) {
            case 'name':
                comparison = a.name.localeCompare(b.name, undefined, { numeric: true });
                break;
            case 'size':
                comparison = (a.size || 0) - (b.size || 0);
                break;
            case 'date':
                const dateA = new Date(a.modified_time || 0);
                const dateB = new Date(b.modified_time || 0);
                comparison = dateA - dateB;
                break;
            case 'type':
                const typeA = a.is_directory ? '文件夹' : getFileExtension(a.name);
                const typeB = b.is_directory ? '文件夹' : getFileExtension(b.name);
                comparison = typeA.localeCompare(typeB);
                break;
        }

        return sortOrder === 'asc' ? comparison : -comparison;
    });
}

// 列表视图
function updateListView(files) {
    const fileList = document.getElementById('ftpFileList');
    const listHeader = document.getElementById('listViewHeader');

    listHeader.style.display = 'block';

    let html = '';

    files.forEach((file, index) => {
        const isSelected = selectedItems.some(item => item.name === file.name);
        const icon = getFileIcon(file);
        const sizeText = file.is_directory ? '' : formatFileSize(file.size);
        const typeText = file.is_directory ? '文件夹' : getFileType(file.name);
        const dateText = formatDateTime(file.modified_time);

        html += `
            <div class="file-item ${isSelected ? 'selected' : ''}"
                 data-index="${index}"
                 onclick="handleFileClick(event, ${index})"
                 ondblclick="handleDoubleClick(event, ${index})"
                 oncontextmenu="handleRightClick(event, ${index})">
                <div class="row g-0 py-2 px-3 align-items-center">
                    <div class="col-5 d-flex align-items-center">
                        <input type="checkbox" class="form-check-input me-2"
                               ${isSelected ? 'checked' : ''}
                               onclick="event.stopPropagation(); toggleFileSelection(${index})">
                        <i class="bi ${icon} me-2 text-primary"></i>
                        <span class="file-name">${escapeHtml(file.name)}</span>
                    </div>
                    <div class="col-2 small text-muted">${sizeText}</div>
                    <div class="col-2 small text-muted">${typeText}</div>
                    <div class="col-3 small text-muted">${dateText}</div>
                </div>
            </div>
        `;
    });

    fileList.innerHTML = html;
}

// 网格视图
function updateGridView(files) {
    const fileList = document.getElementById('ftpFileList');
    const listHeader = document.getElementById('listViewHeader');

    listHeader.style.display = 'none';

    let html = '<div class="row g-2 p-3">';

    files.forEach((file, index) => {
        const isSelected = selectedItems.some(item => item.name === file.name);
        const icon = getFileIcon(file);
        const sizeText = file.is_directory ? '文件夹' : formatFileSize(file.size);

        html += `
            <div class="col-6 col-md-4 col-lg-3">
                <div class="file-grid-item ${isSelected ? 'selected' : ''}"
                     data-index="${index}"
                     onclick="handleFileClick(event, ${index})"
                     ondblclick="handleDoubleClick(event, ${index})"
                     oncontextmenu="handleRightClick(event, ${index})">
                    <div class="text-center p-2">
                        <input type="checkbox" class="form-check-input position-absolute top-0 start-0 m-1"
                               ${isSelected ? 'checked' : ''}
                               onclick="event.stopPropagation(); toggleFileSelection(${index})">
                        <i class="bi ${icon} fa-2x text-primary d-block mb-2"></i>
                        <div class="file-name small text-truncate" title="${escapeHtml(file.name)}">
                            ${escapeHtml(file.name)}
                        </div>
                        <div class="small text-muted">${sizeText}</div>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    fileList.innerHTML = html;
}

// 处理文件点击
function handleFileClick(event, index) {
    // 清除之前的点击超时
    if (clickTimeout) {
        clearTimeout(clickTimeout);
        clickTimeout = null;
    }

    // 延迟执行单击操作，如果在此期间发生双击，则取消单击
    clickTimeout = setTimeout(() => {
        // Ctrl+点击 = 切换选择
        // Shift+点击 = 范围选择
        // 普通点击 = 单选

        if (event.ctrlKey) {
            toggleFileSelection(index);
        } else if (event.shiftKey) {
            // TODO: 实现范围选择
            toggleFileSelection(index);
        } else {
            // 单选
            selectedItems = [];
            toggleFileSelection(index);
        }
        clickTimeout = null;
    }, 200); // 200ms延迟
}

// 处理右键点击
function handleRightClick(event, index) {
    event.preventDefault();

    // 如果右键的项目没有被选中，则选中它
    const file = ftpFileData[index];
    const isSelected = selectedItems.some(item => item.name === file.name);

    if (!isSelected) {
        selectedItems = [];
        toggleFileSelection(index);
    }

    // TODO: 显示右键菜单
    console.log('Right click on:', file.name);
}

// 切换文件选择状态
function toggleFileSelection(index) {
    const file = ftpFileData[index];
    const existingIndex = selectedItems.findIndex(item => item.name === file.name);

    if (existingIndex >= 0) {
        selectedItems.splice(existingIndex, 1);
    } else {
        selectedItems.push({
            name: file.name,
            path: currentPath + (currentPath.endsWith('/') ? '' : '/') + file.name,
            is_directory: file.is_directory,
            size: file.size
        });
    }

    updateFileList(ftpFileData);
    updateSelectedItemsDisplay();
    updateCreateTaskButton();
}

// 处理双击事件
function handleDoubleClick(event, index) {
    // 清除单击超时，防止单击事件执行
    if (clickTimeout) {
        clearTimeout(clickTimeout);
        clickTimeout = null;
    }

    // 阻止事件冒泡
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const file = ftpFileData[index];
    console.log('Double click detected:', file ? file.name : 'undefined', 'is_directory:', file ? file.is_directory : 'undefined');

    if (file && file.is_directory) {
        // 构建新路径
        let newPath = currentPath;
        if (!newPath.endsWith('/')) {
            newPath += '/';
        }
        newPath += file.name;

        console.log('Navigating from', currentPath, 'to:', newPath);
        navigateToPath(newPath);
    }
}

// 导航到指定路径
function navigateToPath(path) {
    console.log('navigateToPath called with:', path);

    // 添加到历史记录
    if (historyIndex === -1 || navigationHistory[historyIndex] !== path) {
        // 如果不在历史末尾，删除后面的记录
        if (historyIndex < navigationHistory.length - 1) {
            navigationHistory = navigationHistory.slice(0, historyIndex + 1);
        }
        navigationHistory.push(path);
        historyIndex = navigationHistory.length - 1;
    }

    currentPath = path;
    document.getElementById('ftpCurrentPath').value = path;
    document.getElementById('addressBar').value = path;

    console.log('About to call loadFTPDirectory for path:', currentPath);
    loadFTPDirectory();
    updateNavigationButtons();
}

// 后退
function navigateBack() {
    if (historyIndex > 0) {
        historyIndex--;
        const path = navigationHistory[historyIndex];
        currentPath = path;
        document.getElementById('ftpCurrentPath').value = path;
        document.getElementById('addressBar').value = path;
        loadFTPDirectory();
        updateNavigationButtons();
    }
}

// 前进
function navigateForward() {
    if (historyIndex < navigationHistory.length - 1) {
        historyIndex++;
        const path = navigationHistory[historyIndex];
        currentPath = path;
        document.getElementById('ftpCurrentPath').value = path;
        document.getElementById('addressBar').value = path;
        loadFTPDirectory();
        updateNavigationButtons();
    }
}

// 向上一级
function navigateUp() {
    if (currentPath !== '/') {
        const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/';
        navigateToPath(parentPath);
    }
}

// 更新导航按钮状态
function updateNavigationButtons() {
    document.getElementById('backBtn').disabled = historyIndex <= 0;
    document.getElementById('forwardBtn').disabled = historyIndex >= navigationHistory.length - 1;
    document.getElementById('upBtn').disabled = currentPath === '/';
}

// 地址栏回车处理
function handleAddressBarEnter(event) {
    if (event.key === 'Enter') {
        navigateToAddressBarPath();
    }
}

// 导航到地址栏路径
function navigateToAddressBarPath() {
    const path = document.getElementById('addressBar').value.trim();
    if (path) {
        navigateToPath(path);
    }
}

// 更新面包屑导航
function updateBreadcrumb() {
    const breadcrumb = document.getElementById('ftpBreadcrumb');
    const pathParts = currentPath.split('/').filter(part => part);

    let html = '<li class="breadcrumb-item"><a href="#" onclick="navigateToPath(\'/\')">根目录</a></li>';

    let currentBreadcrumbPath = '';
    pathParts.forEach((part, index) => {
        currentBreadcrumbPath += '/' + part;
        if (index === pathParts.length - 1) {
            html += `<li class="breadcrumb-item active">${escapeHtml(part)}</li>`;
        } else {
            html += `<li class="breadcrumb-item"><a href="#" onclick="navigateToPath('${currentBreadcrumbPath}')">${escapeHtml(part)}</a></li>`;
        }
    });

    breadcrumb.innerHTML = html;
}

// 设置视图模式
function setViewMode(mode) {
    viewMode = mode;

    // 更新按钮状态
    document.getElementById('listViewBtn').classList.toggle('active', mode === 'list');
    document.getElementById('gridViewBtn').classList.toggle('active', mode === 'grid');

    // 重新渲染文件列表
    updateFileList(ftpFileData);
}

// 设置排序模式
function setSortMode(mode) {
    if (sortMode === mode) {
        // 如果是同一个排序字段，切换排序顺序
        toggleSortOrder();
    } else {
        sortMode = mode;
        sortOrder = 'asc';
    }

    // 重新渲染文件列表
    updateFileList(ftpFileData);
}

// 切换排序顺序
function toggleSortOrder() {
    sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    document.getElementById('sortOrderText').textContent = sortOrder === 'asc' ? '升序' : '降序';

    // 重新渲染文件列表
    updateFileList(ftpFileData);
}

// 全选
function selectAll() {
    selectedItems = ftpFileData.map(file => ({
        name: file.name,
        path: currentPath + (currentPath.endsWith('/') ? '' : '/') + file.name,
        is_directory: file.is_directory,
        size: file.size
    }));
    
    updateFileList(ftpFileData);
    updateSelectedItemsDisplay();
    updateCreateTaskButton();
}

// 清除选择
function clearSelection() {
    selectedItems = [];
    updateFileList(ftpFileData);
    updateSelectedItemsDisplay();
    updateCreateTaskButton();
}

// 更新选中项目显示
function updateSelectedItemsDisplay() {
    const selectedDiv = document.getElementById('selectedItems');
    const selectedList = document.getElementById('selectedItemsList');
    
    if (selectedItems.length === 0) {
        selectedDiv.style.display = 'none';
        return;
    }
    
    selectedDiv.style.display = 'block';
    
    let html = '';
    selectedItems.forEach(item => {
        const icon = item.is_directory ? 'bi-folder' : 'bi-file-earmark';
        html += `<div><i class="bi ${icon}"></i> ${escapeHtml(item.name)}</div>`;
    });
    
    selectedList.innerHTML = html;
}

// 更新任务配置
function updateTaskConfig() {
    const taskType = document.getElementById('ftpTaskType').value;
    const monitorConfig = document.getElementById('monitorConfig');

    if (taskType === 'folder_monitor') {
        monitorConfig.style.display = 'block';
    } else {
        monitorConfig.style.display = 'none';
    }

    updateCreateTaskButton();
}

// 更新创建任务按钮状态
function updateCreateTaskButton() {
    const createBtn = document.getElementById('createTaskBtn');
    const taskType = document.getElementById('ftpTaskType').value;

    console.log('updateCreateTaskButton:', {
        currentSiteId: currentSiteId,
        taskType: taskType,
        selectedItemsLength: selectedItems.length,
        selectedItems: selectedItems
    });

    const canCreate = currentSiteId && taskType && selectedItems.length > 0;
    createBtn.disabled = !canCreate;

    console.log('Button enabled:', !createBtn.disabled);
}

// 刷新FTP目录
function refreshFTPDirectory() {
    if (currentSiteId) {
        loadFTPDirectory();
    }
}

// 测试选中站点的连接
async function testSelectedSiteConnection() {
    const siteId = document.getElementById('ftpSiteSelect').value;
    if (!siteId) {
        showToast('warning', '请先选择FTP站点');
        return;
    }

    try {
        showToast('info', '正在测试连接...');

        const response = await apiRequest(`/sites/api/sites/${siteId}/test`, {
            method: 'POST'
        });

        showToast('success', response.message);

        // 延迟刷新站点列表以获取最新状态
        setTimeout(loadSitesForBrowser, 2000);

    } catch (error) {
        console.error('Connection test failed:', error);
        showToast('error', '连接测试失败: ' + error.message);
    }
}

// 从浏览器创建任务
async function createTaskFromBrowser() {
    const taskType = document.getElementById('ftpTaskType').value;
    const localPath = document.getElementById('ftpLocalPath').value || '/downloads';
    const priority = document.getElementById('taskPriority').value;
    const autoStart = document.getElementById('autoStart').checked;
    
    if (!currentSiteId || !taskType || selectedItems.length === 0) {
        showToast('warning', '请选择站点、任务类型和文件/文件夹');
        return;
    }
    
    try {
        let createdTasks = 0;
        let failedTasks = 0;
        const createBtn = document.getElementById('createTaskBtn');

        // 禁用按钮并显示进度
        createBtn.disabled = true;
        createBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>创建中...';

        for (const item of selectedItems) {
            const taskData = {
                site_id: currentSiteId,
                task_type: taskType,
                remote_path: item.path,
                local_path: localPath,
                priority: priority,
                auto_start: autoStart
            };
            
            // 添加监控特有配置
            if (taskType === 'folder_monitor') {
                taskData.monitor_interval = parseInt(document.getElementById('monitorInterval').value) || 300;
                taskData.file_filter = document.getElementById('fileFilter').value || '';
            }
            
            // 验证任务类型和选择的项目类型是否匹配
            if (taskType === 'file_download' && item.is_directory) {
                console.warn(`文件下载任务不能选择文件夹: ${item.name}`);
                failedTasks++;
                continue;
            }

            if ((taskType === 'folder_download' || taskType === 'folder_monitor') && !item.is_directory) {
                console.warn(`文件夹任务不能选择文件: ${item.name}`);
                failedTasks++;
                continue;
            }

            try {
                // 创建任务
                await apiRequest('/tasks/api/tasks', {
                    method: 'POST',
                    body: JSON.stringify(taskData)
                });

                createdTasks++;
            } catch (itemError) {
                console.error(`创建任务失败 ${item.name}:`, itemError);
                failedTasks++;
            }
        }
        
        // 显示结果
        let message = '';
        if (createdTasks > 0 && failedTasks === 0) {
            message = `成功创建 ${createdTasks} 个任务`;
            showToast('success', message);
        } else if (createdTasks > 0 && failedTasks > 0) {
            message = `成功创建 ${createdTasks} 个任务，${failedTasks} 个失败`;
            showToast('warning', message);
        } else if (failedTasks > 0) {
            message = `所有任务创建失败 (${failedTasks} 个)`;
            showToast('error', message);
        }

        if (createdTasks > 0) {
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('ftpBrowserModal'));
            modal.hide();

            // 刷新任务列表（如果在任务页面）
            if (typeof loadTasks === 'function') {
                setTimeout(loadTasks, 500);
            }
        }
        
    } catch (error) {
        console.error('Failed to create task:', error);
        showToast('error', '创建任务失败: ' + error.message);
    } finally {
        // 恢复按钮状态
        const createBtn = document.getElementById('createTaskBtn');
        createBtn.disabled = false;
        createBtn.innerHTML = '<i class="bi bi-plus-circle me-1"></i>创建任务';
        updateCreateTaskButton(); // 重新检查按钮状态
    }
}

// 调试按钮状态
function debugButtonState() {
    const debugInfo = document.getElementById('debugInfo');
    const createBtn = document.getElementById('createTaskBtn');
    const taskType = document.getElementById('ftpTaskType').value;

    const info = {
        currentSiteId: currentSiteId,
        taskType: taskType,
        selectedItemsLength: selectedItems.length,
        selectedItems: selectedItems.map(item => item.name),
        buttonDisabled: createBtn.disabled
    };

    console.log('Debug button state:', info);

    debugInfo.style.display = 'block';
    debugInfo.innerHTML = `
        <strong>调试信息:</strong><br>
        站点ID: ${currentSiteId || '未选择'}<br>
        任务类型: ${taskType || '未选择'}<br>
        选中项目: ${selectedItems.length} 个<br>
        项目列表: ${selectedItems.map(item => item.name).join(', ') || '无'}<br>
        按钮状态: ${createBtn.disabled ? '禁用' : '启用'}<br>
        <small>条件: ${currentSiteId ? '✓' : '✗'} 站点 + ${taskType ? '✓' : '✗'} 类型 + ${selectedItems.length > 0 ? '✓' : '✗'} 选择</small>
    `;

    // 3秒后隐藏调试信息
    setTimeout(() => {
        debugInfo.style.display = 'none';
    }, 5000);
}
