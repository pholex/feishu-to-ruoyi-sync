#!/usr/bin/env python3
import csv
import os
import sys
import subprocess
import pymysql
import random
from datetime import datetime
from dotenv import load_dotenv

# 修复青龙环境 - 确保QLAPI可用
ql_dir = os.getenv('QL_DIR')
if ql_dir and os.path.exists(ql_dir):
    preload_dir = os.path.join(ql_dir, 'shell', 'preload')
    if os.path.exists(preload_dir) and preload_dir not in sys.path:
        sys.path.insert(0, preload_dir)
        try:
            import client
            import builtins
            if not hasattr(builtins, 'QLAPI'):
                builtins.QLAPI = client.Client()
        except ImportError:
            pass  # 非青龙环境，忽略

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

# 数据库配置
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# 默认用户密码配置（BCrypt加密后的123456）
DEFAULT_USER_PASSWORD_HASH = os.getenv("DEFAULT_USER_PASSWORD_HASH", "$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2")

# Dry-run 模式标志
DRY_RUN = False

# 自动确认标志
AUTO_YES = False

class RuoYiDB:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
    def connect(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                autocommit=False,
                connect_timeout=30,
                read_timeout=30,
                write_timeout=30,
                ssl_disabled=True
            )
            print("✓ 数据库连接成功")
            return True
        except Exception as e:
            print(f"✗ 数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
    
    def get_departments(self):
        """获取部门列表（包括已禁用的）"""
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                sql = "SELECT * FROM sys_dept"  # 获取所有部门，包括已禁用的
                cursor.execute(sql)
                return cursor.fetchall()
        except pymysql.Error as e:
            print(f"✗ 数据库错误: {e}")
            return []
        except Exception as e:
            print(f"✗ 获取部门失败: {e}")
            return []
    
    def create_department(self, dept_data):
        """创建部门"""
        if DRY_RUN:
            print(f"[DRY-RUN] 将创建部门: {dept_data['dept_name']} (level: {dept_data.get('level', 'N/A')})")
            # 返回模拟的dept_id
            import random
            return random.randint(1000, 9999)
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO sys_dept (parent_id, ancestors, dept_name, order_num, 
                                    level, feishu_dept_id, leader, phone, email, 
                                    status, del_flag, create_by, create_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    dept_data['parent_id'],
                    dept_data['ancestors'],
                    dept_data['dept_name'],
                    dept_data['order_num'],
                    dept_data.get('level'),
                    dept_data.get('feishu_dept_id'),
                    dept_data.get('leader', ''),
                    dept_data.get('phone', ''),
                    dept_data.get('email', ''),
                    '0',  # 正常状态
                    '0',  # 未删除
                    'feishu_sync',
                    datetime.now()
                ))
                dept_id = cursor.lastrowid
                self.connection.commit()
                print(f"✓ 创建部门成功: {dept_data['dept_name']} (ID: {dept_id}, level: {dept_data.get('level')})")
                return dept_id
        except pymysql.Error as e:
            self.connection.rollback()
            print(f"✗ 数据库错误: {dept_data['dept_name']} - {e}")
            return None
        except Exception as e:
            self.connection.rollback()
            print(f"✗ 创建部门失败: {dept_data['dept_name']} - {e}")
            return None
    
    def update_department(self, dept_id, dept_data, update_info):
        """更新部门"""
        if DRY_RUN:
            print(f"[DRY-RUN] 将更新部门: {dept_data['dept_name']} ({', '.join(update_info)})")
            return True
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                UPDATE sys_dept SET dept_name = %s, parent_id = %s, ancestors = %s, 
                                  level = %s, update_by = %s, update_time = %s
                WHERE dept_id = %s
                """
                cursor.execute(sql, (
                    dept_data['dept_name'],
                    dept_data['parent_id'],
                    dept_data['ancestors'],
                    dept_data['level'],
                    'feishu_sync',
                    datetime.now(),
                    dept_id
                ))
                self.connection.commit()
                print(f"✓ 更新部门成功: {dept_data['dept_name']} ({', '.join(update_info)})")
                return True
        except pymysql.Error as e:
            self.connection.rollback()
            print(f"✗ 数据库错误: {dept_data['dept_name']} - {e}")
            return False
        except Exception as e:
            self.connection.rollback()
            print(f"✗ 更新部门失败: {dept_data['dept_name']} - {e}")
            return False
    
    def disable_department(self, dept_id, dept_name):
        """禁用部门"""
        if DRY_RUN:
            print(f"[DRY-RUN] 将禁用部门: {dept_name} (ID: {dept_id})")
            return True
            
        try:
            with self.connection.cursor() as cursor:
                sql = "UPDATE sys_dept SET status = '1' WHERE dept_id = %s"
                cursor.execute(sql, (dept_id,))
                self.connection.commit()
                print(f"✓ 禁用部门成功: {dept_name} (ID: {dept_id})")
                return True
        except pymysql.Error as e:
            self.connection.rollback()
            print(f"✗ 禁用部门失败: {dept_name} - {e}")
            return False
    
    def get_users(self):
        """获取用户列表"""
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                sql = "SELECT * FROM sys_user WHERE del_flag = '0'"
                cursor.execute(sql)
                return cursor.fetchall()
        except pymysql.Error as e:
            print(f"✗ 数据库错误: {e}")
            return []
        except Exception as e:
            print(f"✗ 获取用户失败: {e}")
            return []
    
    def create_user(self, user_data):
        """创建用户"""
        if DRY_RUN:
            print(f"[DRY-RUN] 将创建用户: {user_data['user_name']} ({user_data['nick_name']})")
            return random.randint(1000, 9999)
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO sys_user (dept_id, user_name, nick_name, user_type, 
                                    email, phonenumber, sex, password, status, 
                                    del_flag, create_by, create_time, feishu_union_id, feishu_open_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    user_data['dept_id'],
                    user_data['user_name'],
                    user_data['nick_name'],
                    '00',  # 系统用户
                    user_data['email'],
                    user_data.get('phonenumber', ''),
                    user_data.get('sex', '0'),
                    DEFAULT_USER_PASSWORD_HASH,  # 默认密码，可通过环境变量配置
                    '0',  # 正常状态
                    '0',  # 未删除
                    'feishu_sync',
                    datetime.now(),
                    user_data.get('feishu_union_id', ''),
                    user_data.get('feishu_open_id', '')
                ))
                user_id = cursor.lastrowid
                
                # 分配默认角色
                role_sql = "INSERT INTO sys_user_role (user_id, role_id) VALUES (%s, %s)"
                cursor.execute(role_sql, (user_id, 2))  # 普通角色
                
                self.connection.commit()
                print(f"✓ 创建用户成功: {user_data['user_name']} ({user_data['nick_name']})")
                return user_id
        except pymysql.Error as e:
            self.connection.rollback()
            print(f"✗ 数据库错误: {user_data['user_name']} - {e}")
            return None
        except Exception as e:
            self.connection.rollback()
            print(f"✗ 创建用户失败: {user_data['user_name']} - {e}")
            return None
    
    def disable_user(self, user_id, user_name, nick_name):
        """禁用用户"""
        if DRY_RUN:
            print(f"[DRY-RUN] 将禁用用户: {user_name} ({nick_name})")
            return True
            
        try:
            with self.connection.cursor() as cursor:
                sql = "UPDATE sys_user SET status = '1' WHERE user_id = %s"
                cursor.execute(sql, (user_id,))
                self.connection.commit()
                print(f"✓ 禁用用户成功: {user_name} ({nick_name})")
                return True
        except pymysql.Error as e:
            self.connection.rollback()
            print(f"✗ 禁用用户失败: {user_name} - {e}")
            return False

    def update_user(self, user_data, update_info=None):
        """更新用户"""
        if DRY_RUN:
            if update_info and len(update_info) > 0:
                print(f"[DRY-RUN] 将更新用户: {user_data['user_name']} ({user_data['nick_name']}) - {', '.join(update_info)}")
            # 不显示"无需更新"的用户，减少输出噪音
            return True
            
        try:
            with self.connection.cursor() as cursor:
                sql = """
                UPDATE sys_user SET dept_id = %s, nick_name = %s, email = %s, 
                                  phonenumber = %s, sex = %s, update_by = %s, 
                                  update_time = %s, feishu_open_id = %s
                WHERE user_id = %s
                """
                cursor.execute(sql, (
                    user_data['dept_id'],
                    user_data['nick_name'],
                    user_data['email'],
                    user_data.get('phonenumber', ''),
                    user_data.get('sex', '0'),
                    'feishu_sync',
                    datetime.now(),
                    user_data.get('feishu_open_id', ''),
                    user_data['user_id']
                ))
                self.connection.commit()
                if update_info and len(update_info) > 0:
                    print(f"✓ 更新用户成功: {user_data['user_name']} ({user_data['nick_name']}) - {', '.join(update_info)}")
                else:
                    print(f"✓ 更新用户成功: {user_data['user_name']} ({user_data['nick_name']})")
                return True
        except pymysql.Error as e:
            self.connection.rollback()
            print(f"✗ 数据库错误: {user_data['user_name']} - {e}")
            return False
        except Exception as e:
            self.connection.rollback()
            print(f"✗ 更新用户失败: {user_data['user_name']} - {e}")
            return False

def sync_departments(db):
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
    ruoyi_depts = db.get_departments()
    # 使用feishu_dept_id字段进行映射
    ruoyi_dept_map = {}
    for dept in ruoyi_depts:
        feishu_id = dept.get('feishu_dept_id')
        if feishu_id:
            ruoyi_dept_map[feishu_id] = dept
    
    # 构建部门ID映射
    dept_id_map = {}  # feishu_dept_id -> ruoyi_dept_id
    
    # 操作计数器
    dept_created_count = 0
    dept_updated_count = 0
    
    # 按层级创建部门（先创建父部门，再创建子部门）
    def create_dept_recursive(dept_id, feishu_depts_dict):
        nonlocal dept_created_count, dept_updated_count
        
        if dept_id in dept_id_map or dept_id == "0":
            return dept_id_map.get(dept_id, 100)  # 100是若依默认根部门ID
        
        dept = feishu_depts_dict.get(dept_id)
        if not dept:
            return 100
        
        # 先确保父部门存在
        parent_ruoyi_id = create_dept_recursive(dept['parent_dept_id'], feishu_depts_dict)
        
        # 检查部门是否已存在
        if dept_id in ruoyi_dept_map:
            existing_dept = ruoyi_dept_map[dept_id]
            dept_id_map[dept_id] = existing_dept['dept_id']
            
            # 检查是否需要更新
            needs_update = False
            update_info = []
            
            if existing_dept['dept_name'] != dept['dept_name']:
                needs_update = True
                update_info.append(f"名称: {existing_dept['dept_name']} -> {dept['dept_name']}")
            
            if existing_dept.get('level') != int(dept['level']):
                needs_update = True
                update_info.append(f"层级: {existing_dept.get('level', 'N/A')} -> {dept['level']}")
            
            if existing_dept['parent_id'] != parent_ruoyi_id:
                needs_update = True
                update_info.append(f"父部门ID: {existing_dept['parent_id']} -> {parent_ruoyi_id}")
            
            if not existing_dept.get('ancestors'):
                needs_update = True
                update_info.append("ancestors: 空 -> 补充")
            
            if needs_update:
                dept_updated_count += 1
                # 构建ancestors字段
                if parent_ruoyi_id == 100:
                    ancestors = "0,100"
                else:
                    # 查找父部门的ancestors
                    parent_dept = None
                    for d in ruoyi_depts:
                        if d['dept_id'] == parent_ruoyi_id:
                            parent_dept = d
                            break
                    
                    if parent_dept and parent_dept.get('ancestors'):
                        ancestors = f"{parent_dept['ancestors']},{parent_ruoyi_id}"
                    else:
                        ancestors = f"0,100,{parent_ruoyi_id}"
                
                # 准备更新数据
                dept_data = {
                    'dept_name': dept['dept_name'],
                    'parent_id': parent_ruoyi_id,
                    'ancestors': ancestors,
                    'level': int(dept['level'])
                }
                
                # 执行更新
                db.update_department(existing_dept['dept_id'], dept_data, update_info)
            # 不显示"无需更新"的部门，减少输出噪音
            
            return existing_dept['dept_id']
        
        # 构建ancestors字段
        if parent_ruoyi_id == 100:
            ancestors = "0,100"
        else:
            # 查找父部门的ancestors
            parent_dept = None
            # 先在现有部门中查找
            for d in ruoyi_depts:
                if d['dept_id'] == parent_ruoyi_id:
                    parent_dept = d
                    break
            
            if parent_dept and parent_dept.get('ancestors'):
                ancestors = f"{parent_dept['ancestors']},{parent_ruoyi_id}"
            else:
                ancestors = f"0,100,{parent_ruoyi_id}"
        
        # 创建新部门
        dept_data = {
            'dept_name': dept['dept_name'],
            'parent_id': parent_ruoyi_id,
            'ancestors': ancestors,
            'order_num': 0,
            'level': int(dept['level']),
            'feishu_dept_id': dept_id
        }
        
        new_dept_id = db.create_department(dept_data)
        if new_dept_id:
            dept_created_count += 1
            dept_id_map[dept_id] = new_dept_id
            # 更新ruoyi_depts列表
            new_dept = {
                'dept_id': new_dept_id,
                'parent_id': parent_ruoyi_id,
                'ancestors': ancestors,
                'dept_name': dept['dept_name'],
                'level': int(dept['level']),
                'feishu_dept_id': dept_id
            }
            ruoyi_depts.append(new_dept)
            ruoyi_dept_map[dept_id] = new_dept
            return new_dept_id
        
        return parent_ruoyi_id
    
    # 构建飞书部门字典
    feishu_depts_dict = {dept['dept_id']: dept for dept in feishu_depts}
    
    # 统计计数器
    dept_created_count = 0
    dept_updated_count = 0
    dept_unchanged_count = 0
    
    # 按层级顺序创建部门
    for level in range(6):  # level 0-5
        level_depts = [dept for dept in feishu_depts if int(dept['level']) == level]
        print(f"处理 Level {level} 部门: {len(level_depts)} 个")
        
        for dept in level_depts:
            result = create_dept_recursive(dept['dept_id'], feishu_depts_dict)
            # 这里需要修改 create_dept_recursive 来返回操作类型
    
    # 检查需要禁用的部门（在若依中存在但在飞书中不存在的部门）
    feishu_dept_ids = set(dept['dept_id'] for dept in feishu_depts)
    departments_to_disable = []
    
    for dept in ruoyi_depts:
        feishu_id = dept.get('feishu_dept_id')
        if feishu_id and feishu_id not in feishu_dept_ids and dept.get('del_flag') == '0' and dept.get('status') == '0':
            departments_to_disable.append(dept)
    
    # 执行禁用部门
    if departments_to_disable:
        print(f"\n需要禁用的部门: {len(departments_to_disable)} 个")
        for dept in departments_to_disable:
            db.disable_department(dept['dept_id'], dept['dept_name'])
    
    # 部门操作总结
    print(f"\n部门同步总结:")
    print(f"  新建: {dept_created_count} 个, 更新: {dept_updated_count} 个, 禁用: {len(departments_to_disable)} 个")
    print(f"  映射关系: {len(dept_id_map)} 个")
    
    return dept_id_map, ruoyi_depts, ruoyi_dept_map, dept_created_count, dept_updated_count, len(departments_to_disable)

def sync_users(db, dept_id_map, ruoyi_depts, ruoyi_dept_map):
    """同步用户到若依系统"""
    users_csv = get_output_path('feishu_users.csv')
    if not os.path.exists(users_csv):
        print(f"错误: 找不到 {users_csv}，请先运行 fetch_feishu_data.py")
        return 0, 0, [], []
    
    print("正在同步用户...")
    
    # 读取飞书用户列表
    feishu_users = []
    with open(users_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        feishu_users = list(reader)
    
    # 获取若依现有用户
    ruoyi_users = db.get_users()
    
    # 显示用户数量对比
    print(f"用户数量对比: 飞书 {len(feishu_users)} 个，若依 {len(ruoyi_users)} 个")
    
    ruoyi_user_map = {}
    
    # 建立用户映射（使用feishu_union_id）
    for user in ruoyi_users:
        union_id = user.get('feishu_union_id', '')
        if union_id:  # 只有有union_id的用户才加入映射
            ruoyi_user_map[union_id] = user
    
    new_count = 0
    update_count = 0
    new_users = []  # 新建用户明细
    updated_users = []  # 更新用户明细
    
    for feishu_user in feishu_users:
        union_id = feishu_user.get('union_id', '')
        open_id = feishu_user.get('open_id', '')  # 飞书真正的open_id
        user_id = feishu_user['user_id']  # 飞书的user_id（员工工号）
        user_name = feishu_user['user_id']  # 使用user_id作为用户名
        nick_name = feishu_user['name']
        email = feishu_user['enterprise_email']
        dept_id = feishu_user.get('dept_id', '')
        
        # 跳过没有union_id的用户
        if not union_id:
            print(f"⚠️  跳过用户 {user_name} ({nick_name}): 缺少union_id")
            continue
        
        # 获取对应的若依部门ID
        ruoyi_dept_id = dept_id_map.get(dept_id, 100)  # 默认根部门
        
        # 检查用户是否存在（通过union_id匹配）
        existing_user = None
        if union_id in ruoyi_user_map:
            existing_user = ruoyi_user_map[union_id]
        
        user_data = {
            'user_name': user_name,
            'nick_name': nick_name,
            'email': email,
            'phonenumber': '',
            'sex': '0',  # 未知
            'dept_id': ruoyi_dept_id,
            'feishu_union_id': union_id,  # 将union_id存储在feishu_union_id字段中
            'feishu_open_id': open_id  # 将open_id存储在feishu_open_id字段中
        }
        
        if existing_user:
            # 检查需要更新的字段
            update_info = []
            
            if existing_user['nick_name'] != nick_name:
                update_info.append(f"姓名: {existing_user['nick_name']} -> {nick_name}")
            
            if existing_user['email'] != email:
                update_info.append(f"邮箱: {existing_user['email']} -> {email}")
            
            if existing_user['dept_id'] != ruoyi_dept_id:
                # 获取部门名称用于显示
                old_dept_name = "未知部门"
                new_dept_name = "未知部门"
                
                # 查找旧部门名称
                for dept in ruoyi_depts:
                    if dept['dept_id'] == existing_user['dept_id']:
                        old_dept_name = dept['dept_name']
                        break
                
                # 查找新部门名称
                for dept_id, dept in ruoyi_dept_map.items():
                    if dept['dept_id'] == ruoyi_dept_id:
                        new_dept_name = dept['dept_name']
                        break
                
                update_info.append(f"部门: {old_dept_name} -> {new_dept_name}")
            
            if existing_user.get('feishu_open_id', '') != open_id:
                update_info.append(f"飞书OpenID: {existing_user.get('feishu_open_id', '')} -> {open_id}")
            
            # 更新用户
            user_data['user_id'] = existing_user['user_id']
            if update_info and len(update_info) > 0:
                # 只有在有更新内容时才执行更新
                if db.update_user(user_data, update_info):
                    update_count += 1
                    # 收集更新用户明细
                    updated_users.append({
                        'name': nick_name,
                        'user_id': user_name,
                        'changes': ', '.join(update_info)
                    })
            # 如果没有更新内容，不执行任何操作，也不增加计数
        else:
            # 创建新用户
            if db.create_user(user_data):
                new_count += 1
                # 收集新建用户明细
                new_users.append({
                    'name': nick_name,
                    'user_id': user_name
                })
    
    # 处理若依中有但飞书中没有的用户（禁用，除了admin）
    feishu_union_ids = {user.get('union_id', '') for user in feishu_users if user.get('union_id', '')}
    users_to_disable = []
    
    # 检查所有若依用户，找出不在飞书中的用户
    for user in ruoyi_users:
        user_union_id = user.get('feishu_union_id', '')
        # 如果用户有union_id但不在飞书用户中，且不是admin，则禁用
        if user_union_id and user_union_id not in feishu_union_ids and user['user_name'] != 'admin':
            users_to_disable.append(user)
    
    disable_count = 0
    disabled_users = []
    for user in users_to_disable:
        if db.disable_user(user['user_id'], user['user_name'], user['nick_name']):
            disable_count += 1
            disabled_users.append({
                'name': user['nick_name'],
                'user_id': user['user_name']
            })
    
    print(f"\n用户同步总结:")
    print(f"  新建: {new_count} 个, 更新: {update_count} 个, 禁用: {disable_count} 个")
    print(f"  映射关系: {len(feishu_users)} 个")
    
    return new_count, update_count, new_users, updated_users, disable_count, disabled_users

if __name__ == "__main__":
    # 检查命令行参数
    for arg in sys.argv[1:]:
        if arg == '--dry-run':
            DRY_RUN = True
        elif arg == '--yes' or arg == '-y':
            AUTO_YES = True
    
    if DRY_RUN:
        print("=" * 50)
        print("  DRY-RUN 模式 - 预览同步计划（数据库直连版）")
        print("=" * 50)
    else:
        print("=" * 50)
        print("  飞书用户同步到若依系统（数据库直连版）")
        if AUTO_YES:
            print("  自动确认模式 - 跳过所有确认步骤")
        print("=" * 50)
    
    # 检查配置
    if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
        print("错误: 请在 .env 文件中配置数据库连接信息")
        print("需要配置: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
        sys.exit(1)
    
    # 0. 检查飞书数据文件，如果不存在则自动获取
    feishu_users_csv = get_output_path('feishu_users.csv')
    feishu_depts_csv = get_output_path('feishu_departments.csv')
    
    # 使用当前项目目录下的fetch_feishu_data.py
    fetch_script = os.path.join(SCRIPT_DIR, 'fetch_feishu_data.py')
    
    if AUTO_YES or not os.path.exists(feishu_users_csv) or not os.path.exists(feishu_depts_csv):
        print("\n【步骤 0/3】获取飞书数据")
        if AUTO_YES:
            print("自动确认模式：强制重新获取飞书数据...")
        else:
            print("未找到飞书数据文件，正在从飞书获取...")
        
        if os.path.exists(fetch_script):
            result = subprocess.run(['python3', fetch_script], cwd=SCRIPT_DIR)
            if result.returncode != 0:
                print("错误: 获取飞书数据失败")
                sys.exit(1)
            print("✓ 飞书数据获取完成")
        else:
            print(f"错误: 找不到 fetch_feishu_data.py 脚本: {fetch_script}")
            print("请确保 fetch_feishu_data.py 在当前项目目录下")
            sys.exit(1)
    
    # 初始化数据库连接
    db = RuoYiDB(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)
    
    # 连接数据库
    if not db.connect():
        print("错误: 无法连接数据库")
        sys.exit(1)
    
    try:
        # 1. 同步部门
        print("\n【步骤 1/3】同步飞书部门结构到若依系统")
        dept_id_map, ruoyi_depts, ruoyi_dept_map, dept_created_count, dept_updated_count, dept_disabled_count = sync_departments(db)
        
        # 2. 同步用户
        print("\n【步骤 2/3】同步飞书用户到若依系统")
        user_new_count, user_update_count, new_users, updated_users, user_disable_count, disabled_users = sync_users(db, dept_id_map, ruoyi_depts, ruoyi_dept_map)
        
        print("\n" + "=" * 50)
        if DRY_RUN:
            print("  DRY-RUN 完成 - 未执行实际操作")
        else:
            print("  【步骤 3/3】同步完成")
        print("=" * 50)
        
        # 发送青龙通知（如果在青龙环境中运行且有实际操作）
        try:
            if not DRY_RUN and (dept_created_count > 0 or dept_updated_count > 0 or dept_disabled_count > 0 or user_new_count > 0 or user_update_count > 0 or user_disable_count > 0):
                notify_lines = []
                
                # 部门操作
                if dept_created_count > 0:
                    notify_lines.append(f"部门新建: {dept_created_count}个")
                if dept_updated_count > 0:
                    notify_lines.append(f"部门更新: {dept_updated_count}个")
                if dept_disabled_count > 0:
                    notify_lines.append(f"部门禁用: {dept_disabled_count}个")
                
                # 用户新建明细
                if user_new_count > 0:
                    user_names = [f"{user['name']}({user['user_id']})" for user in new_users[:5]]
                    names_str = ', '.join(user_names)
                    if user_new_count > 5:
                        names_str += f"等{user_new_count}个"
                    notify_lines.append(f"用户新建: {names_str}")
                
                # 用户更新明细
                if user_update_count > 0:
                    update_details = []
                    for user in updated_users[:5]:
                        update_details.append(f"{user['name']}({user['user_id']}) - {user['changes']}")
                    
                    details_str = '\n'.join(update_details)
                    if user_update_count > 5:
                        details_str += f"\n...等共{user_update_count}个用户"
                    notify_lines.append(f"用户更新:\n{details_str}")
                
                # 用户禁用明细
                if user_disable_count > 0:
                    disabled_names = [f"{user['name']}({user['user_id']})" for user in disabled_users[:5]]
                    names_str = ', '.join(disabled_names)
                    if user_disable_count > 5:
                        names_str += f"等{user_disable_count}个"
                    notify_lines.append(f"用户禁用: {names_str}")
                
                notify_content = '\n'.join(notify_lines)
                
                QLAPI.systemNotify({
                    "title": "飞书用户同步若依系统完成",
                    "content": notify_content
                })
                print("✓ 青龙系统通知已发送")
        except (NameError, AttributeError):
            # 不在青龙环境中，跳过通知
            if not DRY_RUN and (dept_created_count > 0 or dept_updated_count > 0 or dept_disabled_count > 0 or user_new_count > 0 or user_update_count > 0 or user_disable_count > 0):
                print("⚠ 未检测到青龙环境，跳过系统通知")
        except Exception as e:
            # 其他错误（如网络问题等）
            print(f"⚠ 系统通知发送失败: {e}")
        
    finally:
        # 关闭数据库连接
        db.close()
