#!/usr/bin/env python3
import csv
import requests
import json
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 确保output目录存在
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 路径辅助函数
def get_output_path(filename):
    """获取output目录下文件的绝对路径"""
    return os.path.join(SCRIPT_DIR, 'output', filename)

# 加载环境变量
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

# 若依系统配置
RUOYI_BASE_URL = os.getenv("RUOYI_BASE_URL")
RUOYI_USERNAME = os.getenv("RUOYI_USERNAME")
RUOYI_PASSWORD = os.getenv("RUOYI_PASSWORD")

# 默认用户密码配置
DEFAULT_USER_PASSWORD = os.getenv("DEFAULT_USER_PASSWORD", "123456")

# Dry-run 模式标志
DRY_RUN = False

# 自动确认标志
AUTO_YES = False

class RuoYiAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token = None
        
    def login(self):
        """登录若依系统获取token"""
        login_url = f"{self.base_url}/auth/login"
        login_data = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = self.session.post(login_url, json=login_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                self.token = result.get('data', {}).get('access_token')
                if self.token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.token}'
                    })
                    print("✓ 若依系统登录成功")
                    return True
            
            print(f"✗ 登录失败: {result.get('msg', '未知错误')}")
            return False
            
        except Exception as e:
            print(f"✗ 登录异常: {e}")
            return False
    
    def get_departments(self):
        """获取部门列表"""
        url = f"{self.base_url}/system/dept/list"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                return result.get('data', [])
            else:
                print(f"✗ 获取部门失败: {result.get('msg', '未知错误')}")
                return []
                
        except Exception as e:
            print(f"✗ 获取部门异常: {e}")
            return []
    
    def create_department(self, dept_data):
        """创建部门"""
        if DRY_RUN:
            print(f"[DRY-RUN] 将创建部门: {dept_data['deptName']}")
            return True
            
        url = f"{self.base_url}/system/dept"
        try:
            response = self.session.post(url, json=dept_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                print(f"✓ 创建部门成功: {dept_data['deptName']}")
                return True
            else:
                print(f"✗ 创建部门失败: {dept_data['deptName']} - {result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"✗ 创建部门异常: {dept_data['deptName']} - {e}")
            return False
    
    def get_users(self):
        """获取用户列表"""
        url = f"{self.base_url}/system/user/list"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                return result.get('rows', [])
            else:
                print(f"✗ 获取用户失败: {result.get('msg', '未知错误')}")
                return []
                
        except Exception as e:
            print(f"✗ 获取用户异常: {e}")
            return []
    
    def create_user(self, user_data):
        """创建用户"""
        if DRY_RUN:
            print(f"[DRY-RUN] 将创建用户: {user_data['userName']} ({user_data['nickName']})")
            return True
            
        url = f"{self.base_url}/system/user"
        try:
            response = self.session.post(url, json=user_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                print(f"✓ 创建用户成功: {user_data['userName']} ({user_data['nickName']})")
                return True
            else:
                print(f"✗ 创建用户失败: {user_data['userName']} - {result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"✗ 创建用户异常: {user_data['userName']} - {e}")
            return False
    
    def update_user(self, user_data):
        """更新用户"""
        if DRY_RUN:
            print(f"[DRY-RUN] 将更新用户: {user_data['userName']} ({user_data['nickName']})")
            return True
            
        url = f"{self.base_url}/system/user"
        try:
            response = self.session.put(url, json=user_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                print(f"✓ 更新用户成功: {user_data['userName']} ({user_data['nickName']})")
                return True
            else:
                print(f"✗ 更新用户失败: {user_data['userName']} - {result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"✗ 更新用户异常: {user_data['userName']} - {e}")
            return False

def confirm(prompt, default=True):
    """交互式确认"""
    if DRY_RUN:
        return False
    
    if AUTO_YES:
        print(f"{prompt} [自动确认]")
        return True
    
    default_str = "y/n" if default else "y/n"
    default_hint = "（直接回车默认为 y）" if default else "（直接回车默认为 n）"
    response = input(f"{prompt} [{default_str}] {default_hint}: ").strip().lower()
    
    if response == "":
        return default
    return response in ['y', 'yes']

def sync_departments(api):
    """同步部门到若依系统"""
    dept_csv = get_output_path('feishu_departments.csv')
    if not os.path.exists(dept_csv):
        print(f"错误: 找不到 {dept_csv}，请先运行 fetch_feishu_data.py")
        return {}
    
    print("正在同步部门结构...")
    
    # 读取飞书部门列表
    feishu_depts = []
    with open(dept_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        feishu_depts = list(reader)
    
    # 获取若依现有部门
    ruoyi_depts = api.get_departments()
    # 使用feishu_dept_id作为键进行映射
    ruoyi_dept_map = {}
    for dept in ruoyi_depts:
        feishu_id = dept.get('feishuDeptId')  # 若依中的飞书部门ID字段
        if feishu_id:
            ruoyi_dept_map[feishu_id] = dept
    
    # 构建部门ID映射
    dept_id_map = {}  # feishu_dept_id -> ruoyi_dept_id
    
    # 计算部门层级
    def calculate_level(dept_id, feishu_depts_dict, level_cache={}):
        if dept_id in level_cache:
            return level_cache[dept_id]
        
        if dept_id == "0":
            level_cache[dept_id] = 0
            return 0
        
        dept = feishu_depts_dict.get(dept_id)
        if not dept:
            level_cache[dept_id] = 0
            return 0
        
        parent_level = calculate_level(dept['parent_dept_id'], feishu_depts_dict, level_cache)
        level = parent_level + 1
        level_cache[dept_id] = level
        return level
    
    # 按层级创建部门（先创建父部门，再创建子部门）
    def create_dept_recursive(dept_id, feishu_depts_dict):
        if dept_id in dept_id_map or dept_id == "0":
            return dept_id_map.get(dept_id, 100)  # 100是若依默认根部门ID
        
        dept = feishu_depts_dict.get(dept_id)
        if not dept:
            return 100
        
        # 先确保父部门存在
        parent_ruoyi_id = create_dept_recursive(dept['parent_dept_id'], feishu_depts_dict)
        
        # 检查部门是否已存在（通过feishu_dept_id）
        if dept_id in ruoyi_dept_map:
            dept_id_map[dept_id] = ruoyi_dept_map[dept_id]['deptId']
            return ruoyi_dept_map[dept_id]['deptId']
        
        # 计算部门层级
        level = calculate_level(dept_id, feishu_depts_dict)
        
        # 创建新部门
        dept_data = {
            'deptName': dept['dept_name'],
            'parentId': parent_ruoyi_id,
            'orderNum': 0,
            'status': '0',  # 正常状态
            'level': level,
            'feishuDeptId': dept_id
        }
        
        if api.create_department(dept_data):
            # 重新获取部门列表以获取新创建的部门ID
            updated_depts = api.get_departments()
            for d in updated_depts:
                if d.get('feishuDeptId') == dept_id:
                    dept_id_map[dept_id] = d['deptId']
                    ruoyi_dept_map[dept_id] = d
                    return d['deptId']
        
        return parent_ruoyi_id
    
    # 构建飞书部门字典
    feishu_depts_dict = {dept['dept_id']: dept for dept in feishu_depts}
    
    # 创建所有部门
    for dept in feishu_depts:
        create_dept_recursive(dept['dept_id'], feishu_depts_dict)
    
    print(f"✓ 部门同步完成，映射关系: {len(dept_id_map)} 个")
    return dept_id_map

def sync_users(api, dept_id_map):
    """同步用户到若依系统"""
    users_csv = get_output_path('feishu_users.csv')
    if not os.path.exists(users_csv):
        print(f"错误: 找不到 {users_csv}，请先运行 fetch_feishu_data.py")
        return
    
    print("正在同步用户...")
    
    # 读取飞书用户列表
    feishu_users = []
    with open(users_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        feishu_users = list(reader)
    
    # 获取若依现有用户
    ruoyi_users = api.get_users()
    ruoyi_user_map = {}
    
    # 建立用户映射（优先使用union_id，其次使用用户名）
    for user in ruoyi_users:
        # 如果有remark字段且包含union_id，使用union_id作为键
        if user.get('remark'):
            ruoyi_user_map[user['remark']] = user
        # 否则使用用户名作为键
        ruoyi_user_map[user['userName']] = user
    
    new_count = 0
    update_count = 0
    
    for feishu_user in feishu_users:
        union_id = feishu_user.get('union_id', '')
        user_name = feishu_user['pinyin']
        nick_name = feishu_user['name']
        email = feishu_user['enterprise_email']
        employee_no = feishu_user['employee_no']
        dept_id = feishu_user.get('dept_id', '')
        
        # 获取对应的若依部门ID
        ruoyi_dept_id = dept_id_map.get(dept_id, 100)  # 默认根部门
        
        # 检查用户是否存在（优先通过union_id查找）
        existing_user = None
        if union_id and union_id in ruoyi_user_map:
            existing_user = ruoyi_user_map[union_id]
        elif user_name in ruoyi_user_map:
            existing_user = ruoyi_user_map[user_name]
        
        user_data = {
            'userName': user_name,
            'nickName': nick_name,
            'email': email,
            'phonenumber': '',
            'sex': '0',  # 未知
            'status': '0',  # 正常
            'deptId': ruoyi_dept_id,
            'remark': union_id,  # 将union_id存储在备注字段中
            'roleIds': [2]  # 默认普通角色，需要根据实际情况调整
        }
        
        if existing_user:
            # 更新用户
            user_data['userId'] = existing_user['userId']
            if api.update_user(user_data):
                update_count += 1
        else:
            # 创建新用户
            user_data['password'] = DEFAULT_USER_PASSWORD  # 默认密码，可通过环境变量配置
            if api.create_user(user_data):
                new_count += 1
    
    print(f"✓ 用户同步完成: 新建 {new_count} 个，更新 {update_count} 个")

if __name__ == "__main__":
    # 检查命令行参数
    for arg in sys.argv[1:]:
        if arg == '--dry-run':
            DRY_RUN = True
        elif arg == '--yes' or arg == '-y':
            AUTO_YES = True
    
    if DRY_RUN:
        print("=" * 50)
        print("  DRY-RUN 模式 - 预览同步计划")
        print("=" * 50)
    else:
        print("=" * 50)
        print("  飞书用户同步到若依系统")
        if AUTO_YES:
            print("  自动确认模式 - 跳过所有确认步骤")
        print("=" * 50)
    
    # 检查配置
    if not all([RUOYI_BASE_URL, RUOYI_USERNAME, RUOYI_PASSWORD]):
        print("错误: 请在 .env 文件中配置若依系统连接信息")
        print("需要配置: RUOYI_BASE_URL, RUOYI_USERNAME, RUOYI_PASSWORD")
        sys.exit(1)
    
    # 0. 检查飞书数据文件，如果不存在则自动获取
    feishu_users_csv = get_output_path('feishu_users.csv')
    feishu_depts_csv = get_output_path('feishu_departments.csv')
    
    # 复用feishu-to-ad-sync项目的fetch_feishu_data.py
    fetch_script = os.path.join(os.path.dirname(SCRIPT_DIR), 'feishu-to-ad-sync', 'fetch_feishu_data.py')
    
    if AUTO_YES or not os.path.exists(feishu_users_csv) or not os.path.exists(feishu_depts_csv):
        print("\n【步骤 0/3】获取飞书数据")
        if AUTO_YES:
            print("自动确认模式：强制重新获取飞书数据...")
        else:
            print("未找到飞书数据文件，正在从飞书获取...")
        
        if os.path.exists(fetch_script):
            import subprocess
            # 设置环境变量，让fetch_feishu_data.py将文件保存到当前项目的output目录
            env = os.environ.copy()
            env['OUTPUT_DIR'] = OUTPUT_DIR
            
            result = subprocess.run(['python3', fetch_script], 
                                  cwd=os.path.dirname(fetch_script),
                                  env=env)
            if result.returncode != 0:
                print("错误: 获取飞书数据失败")
                sys.exit(1)
            
            # 复制文件到当前项目
            import shutil
            src_users = os.path.join(os.path.dirname(fetch_script), 'output', 'feishu_users.csv')
            src_depts = os.path.join(os.path.dirname(fetch_script), 'output', 'feishu_departments.csv')
            
            if os.path.exists(src_users):
                shutil.copy2(src_users, feishu_users_csv)
            if os.path.exists(src_depts):
                shutil.copy2(src_depts, feishu_depts_csv)
                
            print("✓ 飞书数据获取完成")
        else:
            print(f"错误: 找不到 fetch_feishu_data.py 脚本: {fetch_script}")
            print("请确保 feishu-to-ad-sync 项目在同级目录下")
            sys.exit(1)
    
    # 初始化若依API
    api = RuoYiAPI(RUOYI_BASE_URL, RUOYI_USERNAME, RUOYI_PASSWORD)
    
    # 登录
    if not api.login():
        print("错误: 无法登录若依系统")
        sys.exit(1)
    
    # 1. 同步部门
    print("\n【步骤 1/3】同步飞书部门结构到若依系统")
    dept_id_map = sync_departments(api)
    
    # 2. 同步用户
    print("\n【步骤 2/3】同步飞书用户到若依系统")
    sync_users(api, dept_id_map)
    
    print("\n" + "=" * 50)
    if DRY_RUN:
        print("  DRY-RUN 完成 - 未执行实际操作")
    else:
        print("  【步骤 3/3】同步完成")
    print("=" * 50)
