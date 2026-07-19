/**
 * API 请求封装
 * 使用 fetch API 替代 axios，避免中文编码问题
 */
const api = {
    _baseURL: '/api',
    
    _getHeaders() {
        const headers = {
            'Content-Type': 'application/json; charset=utf-8',
        };
        const token = localStorage.getItem('token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    },
    
    async _request(method, url, data = null) {
        const options = {
            method,
            headers: this._getHeaders(),
            credentials: 'include',
        };
        if (data) {
            options.body = JSON.stringify(data);
        }
        try {
            const response = await fetch(this._baseURL + url, options);
            const text = await response.text();
            let res;
            try {
                res = JSON.parse(text);
            } catch (e) {
                console.error('JSON parse error:', text);
                throw new Error('响应解析失败');
            }
            if (!response.ok) {
                if (response.status === 401) {
                    localStorage.removeItem('token');
                    localStorage.removeItem('userInfo');
                    ElMessage.warning('登录已过期，请重新登录');
                    window.dispatchEvent(new CustomEvent('auth-expired'));
                    throw new Error('登录已过期');
                }
                ElMessage.error(res.message || '请求失败');
                throw new Error(res.message || 'Error');
            }
            if (res.code !== undefined && res.code !== 200) {
                if (res.message && res.message.includes('Token')) {
                    localStorage.removeItem('token');
                    localStorage.removeItem('userInfo');
                    ElMessage.warning('登录已过期，请重新登录');
                    window.dispatchEvent(new CustomEvent('auth-expired'));
                    throw new Error('登录已过期');
                }
                ElMessage.error(res.message || '请求失败');
                throw new Error(res.message || 'Error');
            }
            return res;
        } catch (e) {
            if (e.message === 'Failed to fetch') {
                ElMessage.error('网络异常，请稍后重试');
            } else if (!e.message.includes('请求失败') && !e.message.includes('登录已过期')) {
                ElMessage.error(e.message || '网络异常');
            }
            throw e;
        }
    },

    getCategories: () => api._request('GET', '/internship/categories'),
    getInternshipList: (params) => {
        const qs = new URLSearchParams(params).toString();
        return api._request('GET', `/internship/list?${qs}`);
    },
    getInternshipDetail: (id) => api._request('GET', `/internship/detail?id=${id}`),

    register: (data) => api._request('POST', '/user/register', data),
    login: (data) => api._request('POST', '/user/login', data),
    getProfile: () => api._request('GET', '/user/profile'),
    updateProfile: (data) => api._request('PATCH', '/user/profile', data),
    changePassword: (data) => api._request('PUT', '/user/password', data),

    getCollects: () => api._request('GET', '/collects/list'),
    toggleCollect: (internshipId) => api._request('POST', `/collects/toggle/${internshipId}`),
    clearCollects: () => api._request('DELETE', '/collects/delete'),

    getHistory: () => api._request('GET', '/history/list'),
    recordHistory: (internshipId) => api._request('POST', `/history/record/${internshipId}`),
    deleteHistory: (recordId) => api._request('DELETE', `/history/${recordId}`),
    clearHistory: () => api._request('DELETE', '/history/'),
};
