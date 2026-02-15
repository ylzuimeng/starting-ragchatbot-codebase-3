"""
测试认证系统的简单脚本
"""
import requests
import json

API_BASE = "http://localhost:8000/api"

print("="*60)
print("测试RAG系统登录功能")
print("="*60)

# 1. 测试注册
print("\n1. 测试用户注册...")
register_data = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123"
}

try:
    response = requests.post(f"{API_BASE}/auth/register", json=register_data)
    if response.status_code == 200:
        data = response.json()
        print("✅ 注册成功！")
        print(f"   用户: {data['user']['username']}")
        print(f"   Token: {data['access_token'][:20]}...")
        token = data['access_token']
    else:
        print(f"❌ 注册失败: {response.status_code}")
        print(response.text)
        token = None
except Exception as e:
    print(f"❌ 注册错误: {e}")
    token = None

# 2. 测试登录（如果注册失败）
if not token:
    print("\n2. 测试用户登录...")
    login_data = {
        "username": "testuser",
        "password": "testpass123"
    }

    try:
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            print("✅ 登录成功！")
            print(f"   用户: {data['user']['username']}")
            token = data['access_token']
        else:
            print(f"❌ 登录失败: {response.status_code}")
            print(response.text)
            token = None
    except Exception as e:
        print(f"❌ 登录错误: {e}")
        token = None

# 3. 测试受保护的端点
if token:
    print("\n3. 测试受保护的API端点...")
    headers = {"Authorization": f"Bearer {token}"}

    # 测试获取用户信息
    try:
        response = requests.get(f"{API_BASE}/auth/me", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("✅ 获取用户信息成功！")
            print(f"   用户ID: {data['id']}")
            print(f"   用户名: {data['username']}")
            print(f"   邮箱: {data['email']}")
        else:
            print(f"❌ 获取用户信息失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取用户信息错误: {e}")

    # 测试课程统计端点
    try:
        response = requests.get(f"{API_BASE}/courses", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ 获取课程统计成功！")
            print(f"   课程总数: {data['total_courses']}")
        else:
            print(f"❌ 获取课程统计失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取课程统计错误: {e}")

# 4. 测试未授权访问
print("\n4. 测试未授权访问...")
try:
    response = requests.get(f"{API_BASE}/courses")
    if response.status_code == 401:
        print("✅ 正确返回401未授权")
    else:
        print(f"⚠️  预期401，实际: {response.status_code}")
except Exception as e:
    print(f"❌ 测试错误: {e}")

print("\n" + "="*60)
print("测试完成！")
print("="*60)
print("\n🌐 访问 http://localhost:8000/login.html 测试前端界面")
print("🌐 访问 http://localhost:8000 查看主界面")
