-- 为超级管理员功能添加新字段
-- 在 Supabase 中执行这个 SQL 脚本

-- 添加超级管理员标识字段
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_super_admin BOOLEAN DEFAULT FALSE NOT NULL;

-- 添加分配管理员权限字段
ALTER TABLE users
ADD COLUMN IF NOT EXISTS can_assign_admin BOOLEAN DEFAULT FALSE NOT NULL;

-- 验证新字段
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('is_super_admin', 'can_assign_admin');