# 飞书用户同步到若依系统操作说明

## 概述
本文档描述如何将飞书（Feishu）的用户和部门数据同步到若依系统的 `sys_user` 和 `sys_dept` 表中。

## 数据库信息
- **数据库名称**: 配置在 .env 文件中
- **数据库主机**: 配置在 .env 文件中
- **引擎**: MySQL 8.0+
- **端口**: 默认 3306

## 涉及的表

### 源数据（飞书CSV文件）
1. **feishu_users.csv** - 飞书用户数据
   - user_id: 用户ID（员工工号字符串，作为用户名）
   - name: 用户姓名
   - union_id: 用户唯一标识
   - enterprise_email: 企业邮箱
   - dept_id: 飞书部门ID
   - dept_name: 飞书部门名称

2. **feishu_departments.csv** - 飞书部门数据
   - dept_id: 飞书部门唯一标识
   - dept_name: 部门名称
   - parent_dept_id: 父部门ID
   - parent_dept_name: 父部门名称
   - level: 部门层级 (0-5)

### 目标表（若依系统的生产数据库）
1. **sys_user** - 系统用户表
   - user_id: 系统用户ID
   - user_name: 用户名（对应飞书user_id字段）
   - dept_id: 部门ID（关联sys_dept表）
   - remark: 备注（存储飞书union_id用于精确匹配）

2. **sys_dept** - 系统部门表
   - dept_id: 部门ID
   - parent_id: 父部门ID
   - dept_name: 部门名称
   - level: 部门层级
   - feishu_dept_id: 飞书部门ID

## 同步操作步骤

### 第一步：准备 sys_dept 表结构

```sql
-- 为 sys_dept 表添加必要字段
ALTER TABLE sys_dept 
ADD COLUMN level INT NULL,
ADD COLUMN feishu_dept_id VARCHAR(50) NULL;
```

### 第二步：同步飞书部门到 sys_dept

通过同步程序读取 feishu_departments.csv 文件，按层级顺序逐层插入部门：

```sql
-- 插入部门的SQL模板（通过程序执行）
INSERT INTO sys_dept (parent_id, dept_name, level, feishu_dept_id, ancestors, order_num, status, del_flag, create_by, create_time)
VALUES (?, ?, ?, ?, ?, 0, '0', '0', 'feishu_sync', NOW());
```

**同步逻辑**：
1. 读取 CSV 文件中的部门数据
2. 按 level 0→1→2→3→4→5 的顺序处理
3. 通过 feishu_dept_id 查找父部门的 dept_id
4. 构建正确的 ancestors 字段
5. 插入新部门记录

### 第三步：同步用户部门关系

通过同步程序读取 feishu_users.csv 文件，创建或更新用户信息：

```sql
-- 创建新用户的SQL模板
INSERT INTO sys_user (dept_id, user_name, nick_name, user_type, email, phonenumber, sex, password, status, del_flag, create_by, create_time, remark)
VALUES (?, ?, ?, '00', ?, '', '0', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'feishu_sync', NOW(), ?);

-- 更新现有用户的SQL模板
UPDATE sys_user 
SET dept_id = ?, nick_name = ?, email = ?, update_by = 'feishu_sync', update_time = NOW(), remark = ?
WHERE user_id = ?;

-- 分配用户角色
INSERT INTO sys_user_role (user_id, role_id) VALUES (?, 2);
```

**同步逻辑**：
1. 读取 CSV 文件中的用户数据
2. 通过 user_id（保存在 sys_user.user_name 字段）匹配现有用户
3. 根据 dept_id 查找对应的若依部门ID
4. 创建新用户或更新现有用户信息

## 关键匹配关系

1. **用户匹配**: 
   - 关系：`sys_user.user_name = feishu_users.user_id`
2. **部门匹配**: `sys_dept.feishu_dept_id = feishu_departments.dept_id`
3. **层级关系**: 通过 `parent_dept_id` 建立父子部门关系
4. **数据源**: 从 CSV 文件读取，通过同步程序处理

## 数据验证

### 验证部门同步
```sql
-- 检查部门总数
SELECT COUNT(*) as total_departments FROM sys_dept;

-- 按层级统计
SELECT level, COUNT(*) as count 
FROM sys_dept 
GROUP BY level 
ORDER BY level;

-- 验证层级关系
SELECT 
    sd1.dept_name,
    sd2.dept_name as parent_name
FROM sys_dept sd1
JOIN sys_dept sd2 ON sd1.parent_id = sd2.dept_id
WHERE sd1.dept_name IN ('美国运营部', '欧洲运营部')
ORDER BY sd1.dept_name;
```

### 验证用户同步
```sql
-- 检查用户部门分配情况
SELECT 
    COUNT(*) as total_users,
    COUNT(dept_id) as users_with_dept,
    COUNT(*) - COUNT(dept_id) as users_without_dept
FROM sys_user;

-- 验证用户匹配准确性（通过union_id）
SELECT 
    su.user_name,
    su.nick_name,
    sd.dept_name as sys_dept,
    su.remark as union_id,
    CASE WHEN su.remark IS NOT NULL AND su.remark != '' THEN '✓ 有union_id' ELSE '✗ 无union_id' END as union_id_status
FROM sys_user su
LEFT JOIN sys_dept sd ON su.dept_id = sd.dept_id
WHERE su.create_by = 'feishu_sync'
LIMIT 10;
```

## 注意事项

1. **数据源**: 使用CSV文件作为数据源，需要通过同步程序处理
2. **层级顺序**：必须按 level 0→1→2→3→4→5 的顺序插入部门，确保父部门先存在
3. **重复部门**：飞书中存在同名部门（如"美国运营部"），通过 feishu_dept_id 区分
4. **用户匹配**：使用 user_id 进行精确匹配，避免用户名冲突
5. **数据一致性**：使用 feishu_dept_id 作为唯一标识，避免名称匹配的歧义
6. **系统账户**：部分系统账户（如 admin）可能不在飞书中，属正常情况

## 故障排除

### 常见问题
1. **部门层级错误**：检查 parent_dept_id 是否正确匹配
2. **用户无部门**：检查 user_name 与飞书 user_id 字段是否一致
3. **重复插入**：使用 feishu_dept_id 确保唯一性
4. **CSV文件格式**：确保CSV文件编码为UTF-8，字段名称正确

### 回滚操作
```sql
-- 清理新增部门（如需重新同步）
DELETE FROM sys_dept WHERE feishu_dept_id IS NOT NULL AND level >= 2;

-- 清理飞书同步的用户（如需重新分配）
DELETE FROM sys_user WHERE create_by = 'feishu_sync';

-- 或者只清理用户部门关系
UPDATE sys_user SET dept_id = NULL WHERE create_by = 'feishu_sync';
```

## 维护建议

1. **定期同步**：建议定期执行同步程序，保持数据一致性
2. **增量更新**：对于新增用户/部门，可单独执行相应的同步操作
3. **数据备份**：同步前建议备份相关表数据
4. **监控验证**：同步后及时验证数据准确性和完整性
5. **日志记录**：同步程序应记录详细的操作日志，便于问题排查

---
*文档更新时间：2025-12-15*
*操作人员：系统管理员*
