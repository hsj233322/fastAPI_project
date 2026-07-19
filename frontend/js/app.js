/**
 * 实习帮 - 主应用
 * Vue 3 + Element Plus (CDN 方式)
 */
const { createApp, ref, reactive, computed, onMounted, nextTick } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;

const app = createApp({
    setup() {
        // ============ 全局状态 ============
        const isLoggedIn = ref(!!localStorage.getItem('token'));
        const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null') || { username: '', avatar: '' });

        const activeMenu = ref('home');

        // ============ 岗位列表 ============
        const categories = ref([]);
        const provinceList = ref([
            '北京', '上海', '广东', '江苏', '浙江', '四川', '湖北', '湖南', '陕西',
            '山东', '河南', '福建', '安徽', '重庆', '天津', '河北', '辽宁', '黑龙江',
            '江西', '广西', '云南', '山西', '甘肃', '新疆', '宁夏', '西藏', '全国'
        ]);

        const educationList = ref([
            { label: '不限', value: '' },
            { label: '中专及以上', value: '中专' },
            { label: '大专及以上', value: '大专' },
            { label: '本科及以上', value: '本科' },
            { label: '硕士及以上', value: '硕士' }
        ]);

        const filters = reactive({
            categoryId: null,
            province: null,
            education: null,
        });

        const page = ref(1);
        const pageSize = ref(12);
        const total = ref(0);
        const jobList = ref([]);
        const listLoading = ref(false);

        // ============ 详情 ============
        const detailVisible = ref(false);
        const detailLoading = ref(false);
        const currentDetail = ref(null);

        // ============ 登录 ============
        const loginVisible = ref(false);
        const loginLoading = ref(false);
        const loginFormRef = ref(null);
        const loginForm = reactive({ username: '', password: '' });
        const loginRules = {
            username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
            password: [
                { required: true, message: '请输入密码', trigger: 'blur' },
                { min: 8, message: '密码至少8位', trigger: 'blur' },
            ],
        };

        // ============ 注册 ============
        const registerVisible = ref(false);
        const registerLoading = ref(false);
        const registerFormRef = ref(null);
        const registerForm = reactive({ username: '', password: '', confirmPassword: '' });
        const registerRules = {
            username: [
                { required: true, message: '请输入用户名', trigger: 'blur' },
                { min: 3, max: 50, message: '3-50位字符', trigger: 'blur' },
                { pattern: /^[a-zA-Z0-9_]+$/, message: '仅支持字母、数字、下划线', trigger: 'blur' },
            ],
            password: [
                { required: true, message: '请输入密码', trigger: 'blur' },
                { min: 8, message: '密码至少8位', trigger: 'blur' },
                {
                    validator: (rule, value, callback) => {
                        if (!/[A-Z]/.test(value)) callback(new Error('需包含大写字母'));
                        else if (!/[a-z]/.test(value)) callback(new Error('需包含小写字母'));
                        else if (!/\d/.test(value)) callback(new Error('需包含数字'));
                        else callback();
                    },
                    trigger: 'blur',
                },
            ],
            confirmPassword: [
                { required: true, message: '请确认密码', trigger: 'blur' },
                {
                    validator: (rule, value, callback) => {
                        if (value !== registerForm.password) callback(new Error('两次密码不一致'));
                        else callback();
                    },
                    trigger: 'blur',
                },
            ],
        };

        // ============ 修改密码 ============
        const passwordVisible = ref(false);
        const passwordLoading = ref(false);
        const passwordFormRef = ref(null);
        const passwordForm = reactive({ old_password: '', new_password: '' });
        const passwordRules = {
            old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
            new_password: [
                { required: true, message: '请输入新密码', trigger: 'blur' },
                { min: 8, message: '密码至少8位', trigger: 'blur' },
                {
                    validator: (rule, value, callback) => {
                        if (!/[A-Z]/.test(value)) callback(new Error('需包含大写字母'));
                        else if (!/[a-z]/.test(value)) callback(new Error('需包含小写字母'));
                        else if (!/\d/.test(value)) callback(new Error('需包含数字'));
                        else callback();
                    },
                    trigger: 'blur',
                },
            ],
        };

        // ============ 个人中心 ============
        const profileVisible = ref(false);
        const profileLoading = ref(false);
        const profileForm = reactive({ avatar: '', bio: '' });

        // ============ 收藏 ============
        const collectList = ref([]);
        const collectLoading = ref(false);
        const collectedIds = ref(new Set());

        // ============ 历史 ============
        const historyList = ref([]);
        const historyLoading = ref(false);

        // ============ 工具函数 ============
        function parseTags(tagsStr) {
            if (!tagsStr) return [];
            // 中文逗号或英文逗号分隔
            return tagsStr.split(/[,，]/).map(s => s.trim()).filter(Boolean);
        }

        function formatTime(timeStr) {
            if (!timeStr) return '';
            const d = new Date(timeStr);
            if (isNaN(d.getTime())) return timeStr;
            const now = new Date();
            const diff = (now - d) / 1000;
            if (diff < 60) return '刚刚';
            if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
            if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
            if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}天前`;
            return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        }

        // ============ 岗位列表相关 ============
        async function loadCategories() {
            try {
                const res = await api.getCategories();
                categories.value = res.data || [];
            } catch (e) {
                console.error('加载分类失败', e);
            }
        }

        async function loadList(resetPage = false) {
            if (resetPage) page.value = 1;
            listLoading.value = true;
            try {
                const params = {
                    page: page.value,
                    pageSize: pageSize.value,
                };
                if (filters.categoryId) params.categoryId = filters.categoryId;
                if (filters.province) params.province = filters.province;
                if (filters.education) params.education = filters.education;

                const res = await api.getInternshipList(params);
                jobList.value = res.data.items || [];
                total.value = res.data.total || 0;
            } catch (e) {
                console.error('加载岗位列表失败', e);
            } finally {
                listLoading.value = false;
            }
        }

        function setCategory(catId) {
            filters.categoryId = catId;
            loadList(true);
        }

        // ============ 详情 ============
        async function openDetail(id) {
            detailVisible.value = true;
            detailLoading.value = true;
            currentDetail.value = null;
            try {
                const res = await api.getInternshipDetail(id);
                currentDetail.value = res.data;
                // 登录用户记录浏览历史（静默处理，不弹错误）
                if (isLoggedIn.value) {
                    api.recordHistory(id).catch(() => { });
                }
            } catch (e) {
                console.error('加载详情失败', e);
            } finally {
                detailLoading.value = false;
            }
        }

        // ============ 收藏 ============
        async function toggleCollect(internshipId) {
            if (!isLoggedIn.value) {
                ElMessage.warning('请先登录');
                showLoginDialog();
                return;
            }
            try {
                const res = await api.toggleCollect(internshipId);
                ElMessage.success(res.message);
                // 更新收藏状态
                if (res.message.includes('收藏成功')) {
                    collectedIds.value.add(internshipId);
                } else if (res.message.includes('取消收藏成功')) {
                    collectedIds.value.delete(internshipId);
                }
                // 如果当前在收藏页，刷新列表
                if (activeMenu.value === 'collects') loadCollects();
            } catch (e) {
                console.error('收藏操作失败', e);
            }
        }

        async function loadCollects() {
            if (!isLoggedIn.value) return;
            collectLoading.value = true;
            try {
                const res = await api.getCollects();
                collectList.value = res.data || [];
                // 更新收藏状态集合
                collectedIds.value.clear();
                collectList.value.forEach(item => {
                    collectedIds.value.add(item.internship_id);
                });
            } catch (e) {
                console.error('加载收藏失败', e);
            } finally {
                collectLoading.value = false;
            }
        }

        async function clearCollects() {
            try {
                await ElMessageBox.confirm('确定清空所有收藏吗？此操作不可恢复', '提示', {
                    type: 'warning',
                });
                const res = await api.clearCollects();
                ElMessage.success(res.message);
                loadCollects();
            } catch (e) {
                if (e !== 'cancel') console.error('清空收藏失败', e);
            }
        }

        // ============ 历史 ============
        async function loadHistory() {
            if (!isLoggedIn.value) return;
            historyLoading.value = true;
            try {
                const res = await api.getHistory();
                historyList.value = res.data || [];
            } catch (e) {
                console.error('加载历史失败', e);
            } finally {
                historyLoading.value = false;
            }
        }

        async function deleteHistory(recordId) {
            try {
                const res = await api.deleteHistory(recordId);
                ElMessage.success(res.message);
                loadHistory();
            } catch (e) {
                console.error('删除历史失败', e);
            }
        }

        async function clearHistory() {
            try {
                await ElMessageBox.confirm('确定清空所有浏览历史吗？', '提示', { type: 'warning' });
                const res = await api.clearHistory();
                ElMessage.success(res.message);
                loadHistory();
            } catch (e) {
                if (e !== 'cancel') console.error('清空历史失败', e);
            }
        }

        // ============ 登录 ============
        function showLoginDialog() {
            loginForm.username = '';
            loginForm.password = '';
            loginVisible.value = true;
        }

        async function doLogin() {
            if (!loginFormRef.value) return;
            try {
                await loginFormRef.value.validate();
                loginLoading.value = true;
                const res = await api.login({
                    username: loginForm.username,
                    password: loginForm.password,
                });
                localStorage.setItem('token', res.data.token);
                localStorage.setItem('userInfo', JSON.stringify(res.data.user_info));
                userInfo.value = res.data.user_info;
                isLoggedIn.value = true;
                loginVisible.value = false;
                ElMessage.success('登录成功');
                // 登录成功后加载收藏状态
                await loadCollects();
            } catch (e) {
                // 校验失败或接口错误
            } finally {
                loginLoading.value = false;
            }
        }

        // ============ 注册 ============
        function showRegisterDialog() {
            registerForm.username = '';
            registerForm.password = '';
            registerForm.confirmPassword = '';
            registerVisible.value = true;
        }

        async function doRegister() {
            if (!registerFormRef.value) return;
            try {
                await registerFormRef.value.validate();
                registerLoading.value = true;
                const res = await api.register({
                    username: registerForm.username,
                    password: registerForm.password,
                });
                ElMessage.success(res.message || '注册成功，请登录');
                registerVisible.value = false;
                // 自动填充登录表单
                loginForm.username = registerForm.username;
                loginForm.password = '';
                showLoginDialog();
            } catch (e) {
                // 校验失败或接口错误
            } finally {
                registerLoading.value = false;
            }
        }

        // ============ 修改密码 ============
        async function doChangePassword() {
            if (!passwordFormRef.value) return;
            try {
                await passwordFormRef.value.validate();
                passwordLoading.value = true;
                const res = await api.changePassword({
                    old_password: passwordForm.old_password,
                    new_password: passwordForm.new_password,
                });
                ElMessage.success(res.message || '密码修改成功，请重新登录');
                passwordVisible.value = false;
                // 密码修改后强制重新登录
                handleLogout();
            } catch (e) {
                // 校验失败或接口错误
            } finally {
                passwordLoading.value = false;
            }
        }

        // ============ 个人中心 ============
        async function openProfile() {
            profileForm.avatar = userInfo.value.avatar || '';
            profileForm.bio = userInfo.value.bio || '';
            profileVisible.value = true;
        }

        async function saveProfile() {
            profileLoading.value = true;
            try {
                const res = await api.updateProfile({
                    avatar: profileForm.avatar || null,
                    bio: profileForm.bio || null,
                });
                userInfo.value = res.data;
                localStorage.setItem('userInfo', JSON.stringify(res.data));
                ElMessage.success('保存成功');
                profileVisible.value = false;
            } catch (e) {
                console.error('保存资料失败', e);
            } finally {
                profileLoading.value = false;
            }
        }

        // ============ 用户菜单 ============
        function handleUserCommand(command) {
            if (command === 'profile') openProfile();
            else if (command === 'password') {
                passwordForm.old_password = '';
                passwordForm.new_password = '';
                passwordVisible.value = true;
            } else if (command === 'logout') handleLogout();
        }

        function handleLogout() {
            localStorage.removeItem('token');
            localStorage.removeItem('userInfo');
            isLoggedIn.value = false;
            userInfo.value = { username: '', avatar: '' };
            activeMenu.value = 'home';
            ElMessage.success('已退出登录');
        }

        // ============ 菜单切换 ============
        function handleMenuSelect(index) {
            activeMenu.value = index;
            if (index === 'collects') loadCollects();
            else if (index === 'history') loadHistory();
            else if (index === 'home') loadList();
        }

        function goHome() {
            activeMenu.value = 'home';
            loadList();
        }

        // ============ 监听 token 失效 ============
        window.addEventListener('auth-expired', () => {
            isLoggedIn.value = false;
            userInfo.value = { username: '', avatar: '' };
            activeMenu.value = 'home';
        });

        // ============ 初始化 ============
        onMounted(() => {
            loadCategories();
            loadList();
        });

        return {
            // 状态
            isLoggedIn, userInfo, activeMenu,
            categories, provinceList, filters,educationList,
            page, pageSize, total, jobList, listLoading,
            detailVisible, detailLoading, currentDetail,
            loginVisible, loginLoading, loginFormRef, loginForm, loginRules,
            registerVisible, registerLoading, registerFormRef, registerForm, registerRules,
            passwordVisible, passwordLoading, passwordFormRef, passwordForm, passwordRules,
            profileVisible, profileLoading, profileForm,
            collectList, collectLoading, collectedIds,
            historyList, historyLoading,
            // Element Plus 图标
            User: ElementPlusIconsVue.User,
            Lock: ElementPlusIconsVue.Lock,
            // 方法
            parseTags, formatTime,
            loadList, setCategory, openDetail,
            toggleCollect, loadCollects, clearCollects,
            loadHistory, deleteHistory, clearHistory,
            showLoginDialog, doLogin,
            showRegisterDialog, doRegister,
            doChangePassword, saveProfile,
            handleUserCommand, handleMenuSelect, goHome,
        };
    },
});

// 注册 Element Plus
app.use(ElementPlus);

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component);
}

app.mount('#app');
