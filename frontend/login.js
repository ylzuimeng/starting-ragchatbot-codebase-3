const API_BASE = '';

// 检查是否已登录
function checkLoggedInStatus() {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || 'null');

    if (token && user) {
        // 已登录，显示提示
        document.getElementById('alreadyLoggedIn').style.display = 'block';
        document.getElementById('loginBox').style.display = 'none';

        // 绑定按钮事件
        document.getElementById('goToHome').addEventListener('click', () => {
            window.location.href = '/';
        });

        document.getElementById('loginAsDifferent').addEventListener('click', () => {
            document.getElementById('alreadyLoggedIn').style.display = 'none';
            document.getElementById('loginBox').style.display = 'block';
        });

        return true;
    }

    return false;
}

// 页面加载时检查登录状态
if (!checkLoggedInStatus()) {
    // 未登录，初始化登录表单
    initializeLoginForms();
}

function initializeLoginForms() {
    // 表单切换
    document.getElementById('showRegister').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('loginForm').style.display = 'none';
        document.getElementById('registerForm').style.display = 'block';
        document.getElementById('formTitle').textContent = '注册';
        clearMessages();
    });

    document.getElementById('showLogin').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('registerForm').style.display = 'none';
        document.getElementById('loginForm').style.display = 'block';
        document.getElementById('formTitle').textContent = '登录';
        clearMessages();
    });

    // 登录处理
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        clearMessages();

        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value;

        if (!username || !password) {
            showError('请填写所有字段');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/auth/login`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                // 保存token和用户信息
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('user', JSON.stringify(data.user));
                // 跳转到主页
                window.location.href = '/';
            } else {
                showError(data.detail || '登录失败');
            }
        } catch (error) {
            showError('网络错误，请稍后重试');
            console.error('Login error:', error);
        }
    });

    // 注册处理
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        clearMessages();

        const username = document.getElementById('regUsername').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const password = document.getElementById('regPassword').value;
        const confirmPassword = document.getElementById('regPasswordConfirm').value;

        if (!username || !email || !password || !confirmPassword) {
            showError('请填写所有字段');
            return;
        }

        if (password !== confirmPassword) {
            showError('两次密码不一致');
            return;
        }

        if (password.length < 8) {
            showError('密码至少需要8个字符');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/auth/register`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, email, password })
            });

            const data = await response.json();

            if (response.ok) {
                // 自动登录
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('user', JSON.stringify(data.user));
                showSuccess('注册成功！正在跳转...');
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                showError(data.detail || '注册失败');
            }
        } catch (error) {
            showError('网络错误，请稍后重试');
            console.error('Register error:', error);
        }
    });
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

function showSuccess(message) {
    const successDiv = document.getElementById('successMessage');
    successDiv.textContent = message;
    successDiv.style.display = 'block';
}

function clearMessages() {
    document.getElementById('errorMessage').style.display = 'none';
    document.getElementById('successMessage').style.display = 'none';
}
