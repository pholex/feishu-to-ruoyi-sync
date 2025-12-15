# 若依系统修改建议

为支持飞书部门同步，需要对若依系统进行以下修改：

## 1. 数据库表修改

在 `sys_dept` 表中添加两个字段：

```sql
ALTER TABLE sys_dept ADD COLUMN `level` int DEFAULT NULL COMMENT '部门层级';
ALTER TABLE sys_dept ADD COLUMN `feishu_dept_id` varchar(50) DEFAULT NULL COMMENT '飞书部门ID';
```

## 2. 实体类修改

修改 `SysDept.java` 实体类，添加新字段：

**文件位置**: `ruoyi-api/ruoyi-api-system/src/main/java/com/ruoyi/system/api/domain/SysDept.java`

在类中添加以下字段和方法：

```java
/** 部门层级 */
private Integer level;

/** 飞书部门ID */
private String feishuDeptId;

public Integer getLevel()
{
    return level;
}

public void setLevel(Integer level)
{
    this.level = level;
}

public String getFeishuDeptId()
{
    return feishuDeptId;
}

public void setFeishuDeptId(String feishuDeptId)
{
    this.feishuDeptId = feishuDeptId;
}
```

并在 `toString()` 方法中添加：

```java
.append("level", getLevel())
.append("feishuDeptId", getFeishuDeptId())
```

## 3. Mapper 修改

修改 `SysDeptMapper.xml` 文件：

**文件位置**: `ruoyi-modules/ruoyi-system/src/main/resources/mapper/system/SysDeptMapper.xml`

### 3.1 修改 resultMap

```xml
<result property="level"         column="level"         />
<result property="feishuDeptId"  column="feishu_dept_id" />
```

### 3.2 修改查询字段

在 `select` 语句中添加：

```xml
d.level, d.feishu_dept_id
```

### 3.3 修改插入语句

在 `insertDept` 中添加：

```xml
<if test="level != null">level,</if>
<if test="feishuDeptId != null and feishuDeptId != ''">feishu_dept_id,</if>
```

对应的值：

```xml
<if test="level != null">#{level},</if>
<if test="feishuDeptId != null and feishuDeptId != ''">#{feishuDeptId},</if>
```

### 3.4 修改更新语句

在 `updateDept` 中添加：

```xml
<if test="level != null">level = #{level},</if>
<if test="feishuDeptId != null and feishuDeptId != ''">feishu_dept_id = #{feishuDeptId},</if>
```

## 4. 前端修改（可选）

如果需要在前端显示这些字段，可以修改部门管理页面：

**文件位置**: `ruoyi-ui/src/views/system/dept/index.vue`

在表格中添加列：

```vue
<el-table-column prop="level" label="层级" width="80"></el-table-column>
<el-table-column prop="feishuDeptId" label="飞书部门ID" width="120"></el-table-column>
```

在表单中添加字段（如果需要手动编辑）：

```vue
<el-form-item label="部门层级" prop="level">
  <el-input-number v-model="form.level" :min="0" controls-position="right" placeholder="请输入部门层级" />
</el-form-item>
<el-form-item label="飞书部门ID" prop="feishuDeptId">
  <el-input v-model="form.feishuDeptId" placeholder="请输入飞书部门ID" maxlength="50" />
</el-form-item>
```

## 5. 验证修改

修改完成后，可以通过以下方式验证：

1. 重启若依系统
2. 运行飞书同步脚本
3. 检查数据库中 `sys_dept` 表的新字段是否正确填充
4. 通过若依管理界面查看部门信息

## 注意事项

1. 修改前请备份数据库
2. 建议在测试环境先验证修改效果
3. `feishu_dept_id` 字段应该是唯一的，可以考虑添加唯一索引：
   ```sql
   ALTER TABLE sys_dept ADD UNIQUE INDEX idx_feishu_dept_id (feishu_dept_id);
   ```
