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
                    // 判断是否为登录或注册接口
                    const isAuthRequest = url.includes('/login') || url.includes('/register');
                    if (!isAuthRequest) {
                        // 只有非登录接口的 401 才算 token 过期
                        localStorage.removeItem('token');
                        localStorage.removeItem('userInfo');
                        ElMessage.warning('登录已过期，请重新登录');
                        const err = new Error('登录已过期');
                        err._shown = true;
                        throw err;
                    } else {
                        // 登录/注册失败，直接显示后端返回的错误信息
                        ElMessage.error(res.message || '认证失败');
                        const err = new Error(res.message || '认证失败');
                        err._shown = true;
                        throw err;
                    }
                }
                ElMessage.error(res.message || '请求失败');
                const err1 = new Error(res.message || '请求失败');
                err1._shown = true;
                throw err1;
            }
            
            if (res.code !== undefined && res.code !== 200) {
                if (res.message && res.message.includes('Token')) {
                    localStorage.removeItem('token');
                    localStorage.removeItem('userInfo');
                    ElMessage.warning('登录已过期，请重新登录');
                    const err = new Error('登录已过期');
                    err._shown = true;
                    throw err;
                }
                ElMessage.error(res.message || '请求失败');
                const err2 = new Error(res.message || '请求失败');
                err2._shown = true;
                throw err2;
            }
            return res;
        } catch (e) {
            if (e.message === 'Failed to fetch') {
                ElMessage.error('网络异常，请稍后重试');
            } else if (!e._shown) {
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

    /**
     * AI 对话（SSE 流式）
     * @param {Object} data { message, session_id }
     * @param {Object} handlers { onReasoning, onStatus, onDelta, onJobs, onDone, onError }
     * 流建立前的错误（401/429/422）仍为普通 JSON；建立后的错误走 error 事件。
     */
    async chatAIStream(data, handlers = {}) {
        const { onReasoning, onStatus, onDelta, onJobs, onDone, onError } = handlers;

        let response;
        try {
            response = await fetch(this._baseURL + '/ai/chat/stream', {
                method: 'POST',
                headers: this._getHeaders(),
                credentials: 'include',
                body: JSON.stringify(data),
            });
        } catch (e) {
            ElMessage.error('网络异常，请稍后重试');
            throw e;
        }

        if (!response.ok || !response.body) {
            let detail = '';
            try {
                const res = await response.json();
                detail = (typeof res.detail === 'string' && res.detail) || res.message || '';
            } catch (_) { /* 非 JSON 错误体 */ }
            if (response.status === 401) {
                localStorage.removeItem('token');
                localStorage.removeItem('userInfo');
                ElMessage.warning('登录已过期，请重新登录');
                window.dispatchEvent(new Event('auth-expired'));
            } else {
                ElMessage.error(detail || `请求失败(${response.status})`);
            }
            throw new Error(detail || 'stream request failed');
        }

        const dispatchFrame = (rawFrame) => {
            // 一帧内可能有多行 data:，按 SSE 规范用换行拼接
            const dataLines = rawFrame
                .split('\n')
                .filter((line) => line.startsWith('data:'))
                .map((line) => line.slice(5).replace(/^ /, ''));
            if (!dataLines.length) return;
            const payload = JSON.parse(dataLines.join('\n'));
            if (payload.type === 'reasoning') onReasoning?.(payload.content);
            else if (payload.type === 'delta') onDelta?.(payload.content);
            else if (payload.type === 'status') onStatus?.(payload.content);
            else if (payload.type === 'jobs') onJobs?.(payload.content);
            else if (payload.type === 'done') onDone?.(payload);
            else if (payload.type === 'error') onError?.(payload.content);
        };

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            let sepIndex;
            // SSE 以空行（\n\n）分隔事件
            while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
                const rawFrame = buffer.slice(0, sepIndex);
                buffer = buffer.slice(sepIndex + 2);
                try {
                    dispatchFrame(rawFrame);
                } catch (e) {
                    console.error('SSE 帧解析失败', e, rawFrame);
                }
            }
        }
    },
};
