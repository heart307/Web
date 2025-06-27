// 站点管理JavaScript

let currentSiteId = null;
let sitesData = [];

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeSitesPage();
});

// 初始化站点页面
function initializeSitesPage() {
    loadSites();
    loadSiteGroups();

    // 设置定时刷新
    setInterval(loadSites, 30000); // 30秒刷新一次

    // 设置活跃测试状态检查
    setInterval(checkActiveTests, 5000); // 5秒检查一次活跃测试

    console.log('Sites page initialized');
}

// 加载站点列表
async function loadSites() {
    try {
        console.log('Loading sites...');
        const data = await apiRequest('/sites/api/sites');
        console.log('Sites data received:', data);
        sitesData = data.sites;
        updateSitesTable(sitesData);
        updateSitesStats(sitesData);
        console.log('Sites loaded successfully:', sitesData.length, 'sites');
    } catch (error) {
        console.error('Failed to load sites:', error);
        showToast('error', '加载站点列表失败: ' + error.message);
    }
}

// 更新站点统计信息
function updateSitesStats(sites) {
    const totalSites = sites.length;
    const connectedSites = sites.filter(s => s.status === 'connected').length;
    const disconnectedSites = sites.filter(s => s.status === 'disconnected').length;
    
    // 获取分组数
    const groups = new Set(sites.map(s => s.group || '默认分组'));
    const groupsCount = groups.size;
    
    // 更新统计卡片
    updateStatCard('total-sites-count', totalSites);
    updateStatCard('connected-sites-count', connectedSites);
    updateStatCard('disconnected-sites-count', disconnectedSites);
    updateStatCard('groups-count', groupsCount);
}

// 更新站点表格
function updateSitesTable(sites) {
    const tbody = document.getElementById('sites-tbody');
    if (!tbody) return;
    
    if (sites.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    <div class="empty-state">
                        <i class="bi bi-server"></i>
                        <h5>暂无站点</h5>
                        <p>点击"添加站点"按钮创建第一个FTP站点</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = sites.map(site => `
        <tr>
            <td>
                <strong>${escapeHtml(site.name)}</strong>
                <br>
                <small class="text-muted">${escapeHtml(site.id)}</small>
            </td>
            <td>
                <code>${escapeHtml(site.host)}:${site.port}</code>
                <br>
                <small class="text-muted">${escapeHtml(site.username || '匿名')}</small>
            </td>
            <td>
                <span class="badge bg-info">${escapeHtml(site.protocol.toUpperCase())}</span>
            </td>
            <td>
                <span class="badge bg-secondary">${escapeHtml(site.group || '默认分组')}</span>
            </td>
            <td>${getConnectionStatus(site.status || 'unknown')}</td>
            <td>
                <small class="text-muted">${formatDateTime(site.last_check)}</small>
                ${site.connection_time ? `<br><small class="text-success">${site.connection_time.toFixed(2)}s</small>` : ''}
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-primary" onclick="showSiteDetail('${site.id}')" title="查看详情">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-outline-warning" onclick="testSiteConnection('${site.id}')" title="测试连接">
                        <i class="bi bi-wifi"></i>
                    </button>
                    <button class="btn btn-outline-info" onclick="refreshSiteStatus('${site.id}')" title="刷新状态">
                        <i class="bi bi-arrow-clockwise"></i>
                    </button>
                    <button class="btn btn-outline-success" onclick="editSite('${site.id}')" title="编辑">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteSite('${site.id}')" title="删除">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// HTML转义函数
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 更新统计卡片
function updateStatCard(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.add('updating');
        setTimeout(() => {
            element.textContent = value;
            element.classList.remove('updating');
        }, 200);
    }
}

// 刷新站点列表
function refreshSites(event) {
    const refreshBtn = event ? event.target.closest('button') : null;
    if (refreshBtn) {
        refreshBtn.classList.add('btn-refresh', 'refreshing');

        loadSites().finally(() => {
            setTimeout(() => {
                refreshBtn.classList.remove('refreshing');
            }, 300);
        });
    } else {
        loadSites();
    }
}

// 筛选站点
function filterSites(type, value) {
    let filteredSites = sitesData;
    
    if (type === 'status' && value !== 'all') {
        filteredSites = sitesData.filter(site => site.status === value);
    } else if (type === 'group' && value !== 'all') {
        // 这里可以添加按分组筛选的逻辑
        showToast('info', '按分组筛选功能开发中...');
        return;
    }
    
    updateSitesTable(filteredSites);
    showToast('info', `筛选结果: ${filteredSites.length} 个站点`);
}

// 测试所有连接
async function testAllConnections() {
    if (sitesData.length === 0) {
        showToast('warning', '没有可测试的站点');
        return;
    }

    try {
        showToast('info', `开始批量测试 ${sitesData.length} 个站点的连接...`);

        const response = await apiRequest('/sites/api/sites/test-all', {
            method: 'POST'
        });

        showToast('success', response.message);

        // 延迟刷新数据
        setTimeout(loadSites, 3000);

    } catch (error) {
        console.error('Batch connection test failed:', error);
        showToast('error', '批量连接测试失败: ' + error.message);
    }
}

// 显示站点详情
async function showSiteDetail(siteId) {
    try {
        const data = await apiRequest(`/sites/api/sites/${siteId}`);
        const site = data.site;
        
        // 填充详情信息
        document.getElementById('detail-name').textContent = site.name;
        document.getElementById('detail-host').textContent = site.host;
        document.getElementById('detail-port').textContent = site.port;
        document.getElementById('detail-username').textContent = site.username || '匿名';
        document.getElementById('detail-protocol').textContent = site.protocol.toUpperCase();
        document.getElementById('detail-group').textContent = site.group || '默认分组';
        document.getElementById('detail-status').innerHTML = getConnectionStatus(site.status || 'unknown');
        document.getElementById('detail-last-check').textContent = formatDateTime(site.last_check);
        document.getElementById('detail-connection-time').textContent = site.connection_time ? `${site.connection_time.toFixed(2)}秒` : '-';
        document.getElementById('detail-created-by').textContent = site.created_by || '-';
        document.getElementById('detail-created-at').textContent = formatDateTime(site.created_at);
        
        // 设置当前站点ID
        currentSiteId = siteId;
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('siteDetailModal'));
        modal.show();
        
    } catch (error) {
        showToast('error', '获取站点详情失败: ' + error.message);
    }
}

// 浏览站点目录
async function browseSiteDirectory() {
    if (!currentSiteId) return;
    
    const path = document.getElementById('browse-path').value || '/';
    const listingDiv = document.getElementById('directory-listing');
    
    try {
        listingDiv.innerHTML = '<div class="text-center"><i class="bi bi-hourglass-split"></i> 加载中...</div>';
        
        const data = await apiRequest(`/sites/api/sites/${currentSiteId}/browse`, {
            method: 'POST',
            body: JSON.stringify({ path: path })
        });
        
        const files = data.files;
        
        if (files.length === 0) {
            listingDiv.innerHTML = '<div class="text-muted text-center">目录为空</div>';
            return;
        }
        
        listingDiv.innerHTML = files.map(file => `
            <div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                <div>
                    <i class="bi bi-${file.is_directory ? 'folder' : 'file-earmark'} me-2"></i>
                    <span>${escapeHtml(file.name)}</span>
                </div>
                <div class="text-muted small">
                    ${file.is_directory ? '目录' : formatFileSize(file.size)}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        listingDiv.innerHTML = `<div class="text-danger">浏览失败: ${error.message}</div>`;
    }
}

// 测试站点连接
async function testSiteConnection(siteId = null) {
    const targetSiteId = siteId || currentSiteId;
    if (!targetSiteId) return;
    
    try {
        const response = await apiRequest(`/sites/api/sites/${targetSiteId}/test`, {
            method: 'POST'
        });
        
        showToast('success', response.message);
        
        // 延迟刷新数据
        setTimeout(loadSites, 1000);
        
    } catch (error) {
        showToast('error', '测试连接失败: ' + error.message);
    }
}

// 编辑站点
async function editSite(siteId = null) {
    const targetSiteId = siteId || currentSiteId;
    if (!targetSiteId) return;
    
    try {
        const data = await apiRequest(`/sites/api/sites/${targetSiteId}`);
        const site = data.site;
        
        // 填充编辑表单
        document.getElementById('edit-site-id').value = site.id;
        document.getElementById('edit-site-name').value = site.name;
        document.getElementById('edit-site-host').value = site.host;
        document.getElementById('edit-site-port').value = site.port;
        document.getElementById('edit-site-username').value = site.username || '';
        document.getElementById('edit-site-password').value = ''; // 密码不回填
        document.getElementById('edit-site-protocol').value = site.protocol;
        document.getElementById('edit-site-group').value = site.group || '';
        
        // 关闭详情模态框
        const detailModal = bootstrap.Modal.getInstance(document.getElementById('siteDetailModal'));
        if (detailModal) {
            detailModal.hide();
        }
        
        // 显示编辑模态框
        const editModal = new bootstrap.Modal(document.getElementById('editSiteModal'));
        editModal.show();
        
    } catch (error) {
        showToast('error', '获取站点信息失败: ' + error.message);
    }
}

// 更新站点
async function updateSite() {
    const form = document.getElementById('editSiteForm');
    const formData = new FormData(form);
    
    const siteId = document.getElementById('edit-site-id').value;
    const siteData = {
        name: formData.get('siteName') || document.getElementById('edit-site-name').value,
        host: document.getElementById('edit-site-host').value,
        port: parseInt(document.getElementById('edit-site-port').value),
        username: document.getElementById('edit-site-username').value,
        protocol: document.getElementById('edit-site-protocol').value,
        group: document.getElementById('edit-site-group').value
    };
    
    // 如果密码不为空，则包含密码
    const password = document.getElementById('edit-site-password').value;
    if (password) {
        siteData.password = password;
    }
    
    try {
        const response = await apiRequest(`/sites/api/sites/${siteId}`, {
            method: 'PUT',
            body: JSON.stringify(siteData)
        });
        
        showToast('success', response.message);
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('editSiteModal'));
        modal.hide();
        
        // 刷新数据
        loadSites();
        
    } catch (error) {
        showToast('error', '更新站点失败: ' + error.message);
    }
}

// 删除站点
async function deleteSite(siteId = null) {
    const targetSiteId = siteId || document.getElementById('edit-site-id').value;
    if (!targetSiteId) return;
    
    // 获取站点名称用于确认
    const site = sitesData.find(s => s.id === targetSiteId);
    const siteName = site ? site.name : '该站点';
    
    if (!confirm(`确定要删除站点"${siteName}"吗？此操作不可撤销。`)) {
        return;
    }
    
    try {
        const response = await apiRequest(`/sites/api/sites/${targetSiteId}`, {
            method: 'DELETE'
        });
        
        showToast('success', response.message);
        
        // 关闭所有相关模态框
        const editModal = bootstrap.Modal.getInstance(document.getElementById('editSiteModal'));
        if (editModal) {
            editModal.hide();
        }
        
        const detailModal = bootstrap.Modal.getInstance(document.getElementById('siteDetailModal'));
        if (detailModal) {
            detailModal.hide();
        }
        
        // 刷新数据
        loadSites();
        
    } catch (error) {
        showToast('error', '删除站点失败: ' + error.message);
    }
}

// 刷新单个站点状态
async function refreshSiteStatus(siteId) {
    try {
        console.log('Refreshing status for site:', siteId);

        // 先测试连接
        await testSiteConnection(siteId);

        // 延迟刷新站点列表以获取最新状态
        setTimeout(async () => {
            await loadSites();
            showToast('info', '站点状态已刷新');
        }, 2000);

    } catch (error) {
        console.error('Failed to refresh site status:', error);
        showToast('error', '刷新站点状态失败: ' + error.message);
    }
}

// 检查活跃的连接测试
async function checkActiveTests() {
    try {
        const data = await apiRequest('/sites/api/sites/active-tests');
        const activeTests = data.active_tests;
        const activeCount = data.count;

        // 更新UI显示活跃测试状态
        updateActiveTestsUI(activeTests, activeCount);

    } catch (error) {
        // 静默处理错误，避免频繁的错误提示
        console.debug('Failed to check active tests:', error);
    }
}

// 更新活跃测试的UI显示
function updateActiveTestsUI(activeTests, activeCount) {
    // 更新站点表格中的测试状态
    const tbody = document.getElementById('sites-tbody');
    if (!tbody) return;

    // 为正在测试的站点添加视觉指示
    Object.keys(activeTests).forEach(siteId => {
        const isActive = activeTests[siteId];
        const rows = tbody.querySelectorAll('tr');

        rows.forEach(row => {
            const siteIdElement = row.querySelector('small.text-muted');
            if (siteIdElement && siteIdElement.textContent === siteId) {
                const testButton = row.querySelector('button[onclick*="testSiteConnection"]');
                if (testButton) {
                    if (isActive) {
                        testButton.classList.add('btn-warning');
                        testButton.classList.remove('btn-outline-warning');
                        testButton.innerHTML = '<i class="bi bi-hourglass-split"></i>';
                        testButton.disabled = true;
                        testButton.title = '正在测试连接...';
                    } else {
                        testButton.classList.remove('btn-warning');
                        testButton.classList.add('btn-outline-warning');
                        testButton.innerHTML = '<i class="bi bi-wifi"></i>';
                        testButton.disabled = false;
                        testButton.title = '测试连接';
                    }
                }
            }
        });
    });

    // 更新统计信息
    if (activeCount > 0) {
        console.log(`当前有 ${activeCount} 个站点正在进行连接测试`);
    }
}

// 加载站点分组
async function loadSiteGroups() {
    try {
        const data = await apiRequest('/sites/api/sites/groups');
        // 这里可以用分组数据更新UI，比如筛选下拉框
        console.log('Site groups loaded:', data.groups);
    } catch (error) {
        console.error('Failed to load site groups:', error);
    }
}
