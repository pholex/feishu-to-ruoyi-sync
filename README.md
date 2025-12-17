# 飞书用户同步到若依系统

将飞书通讯录中的用户和部门信息同步到若依(RuoYi)管理系统。

## 功能特性

- 自动获取飞书部门和用户数据
- 同步部门结构到若依系统
- 同步用户信息到若依系统
- 支持 Dry-run 模式预览同步计划
- 支持青龙面板定时任务和通知

## 使用步骤

### 1. 配置若依系统（首次使用）

参考 [若依系统配置](docs/RUOYI_SETUP.md) 配置若依系统数据库表结构。

#### 扩展用户表结构

执行以下 SQL 语句扩展 sys_user 表以支持飞书字段：

```sql
-- 扩展用户表，添加飞书相关字段
ALTER TABLE sys_user 
ADD COLUMN feishu_open_id VARCHAR(100) COMMENT '飞书OpenID',
ADD COLUMN feishu_union_id VARCHAR(100) COMMENT '飞书UnionID';

-- 为飞书字段添加索引
CREATE INDEX idx_sys_user_feishu_open_id ON sys_user(feishu_open_id);
CREATE INDEX idx_sys_user_feishu_union_id ON sys_user(feishu_union_id);
```

### 2. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/) 创建企业自建应用
2. 获取 App ID 和 App Secret
3. 添加以下权限（应用权限-租户级别）：

```json
{
  "scopes": {
    "tenant": [
      "contact:contact.base:readonly",
      "contact:department.base:readonly", 
      "contact:department.organize:readonly",
      "contact:user.base:readonly",
      "contact:user.department:readonly",
      "contact:user.email:readonly",
      "contact:user.employee:readonly",
      "contact:user.employee_id:readonly",
      "directory:department.count:read",
      "directory:department.status:read",
      "directory:department:list",
      "tenant:tenant:readonly"
    ],
    "user": []
  }
}
```

注：`tenant:tenant:readonly` 用于获取企业名称

### 3. 配置环境变量

```bash
# 将 .env.example 文件重命名为 .env
# 编辑 .env 文件，填入飞书应用信息和数据库配置
```

### 4. 安装依赖并运行

```bash
pip install -r requirements.txt

# 预览模式（推荐首次使用）
python3 sync_to_ruoyi_db.py --dry-run

# 正式同步
python3 sync_to_ruoyi_db.py
```

## 同步流程

1. 获取飞书数据（用户和部门）
2. 同步部门结构到若依系统
3. 对比飞书和若依用户，生成同步计划
4. 创建新用户或更新现有用户信息

## 字段映射

| 飞书字段 | 若依字段 | 说明 |
|---------|---------|------|
| user_id | user_name | 用户登录名 |
| name | nick_name | 用户显示名称 |
| enterprise_email | email | 企业邮箱 |
| union_id | feishu_union_id | 飞书唯一标识（跨应用） |
| open_id | feishu_open_id | 飞书OpenID（应用级） |
| dept_id | dept_id | 部门关联（通过feishu_dept_id匹配） |

## 文档

- [若依系统配置](docs/RUOYI_SETUP.md) - 系统配置说明
- [数据库同步指南](docs/DB_SYNC_GUIDE.md) - 技术实现细节

## 注意事项

- 首次使用建议先运行 `--dry-run` 模式查看同步计划
- 输出文件保存在 `./output/` 目录
- 支持青龙面板定时任务，同步完成后会自动发送系统通知
