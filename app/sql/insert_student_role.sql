-- ============================================================
-- 校园学生事务问答系统：学生角色 + 学生账号初始化
-- ============================================================
-- 背景（对应后端权限收敛改动）：
--   聊天/会话相关接口的权限已统一为 ai:chat:talk
--   /knowledgeBase/scope（聊天页的知识库选择器）也改为 ai:chat:talk
--   因此学生角色只需要一个权限：ai:chat:talk
--
-- 效果：
--   学生登录后侧边栏只能看到「AI助手 → 对话问答」
--   看不到 系统管理 / 知识库管理 / 文档管理 / 监控 等后台页面
--   学生能用聊天页：加载会话、加载知识库下拉、RAG 问答
-- ============================================================

-- 1. 创建「学生」角色
--    data_scope='5'（仅本人）：公共知识库检索按 kb_id 过滤、不按部门隔离，
--    所以这里的 data_scope 不影响学生读公共库。
INSERT INTO "public"."sys_role"
  ("role_name", "role_key", "role_sort", "data_scope", "status", "del_flag", "create_by", "create_time")
VALUES
  ('学生', 'student', 2, '5', '0', '0', 'admin', now());

-- 2. 给 student 角色分配菜单：目录 2（AI助手）+ 菜单 202（对话问答，perms=ai:chat:talk）
--    不给菜单 200（知识库管理）/ 201（文档管理）/ 系统管理目录，学生自然看不到那些页面。
INSERT INTO "public"."sys_role_menu" ("role_id", "menu_id")
SELECT r.role_id, m.menu_id
FROM "public"."sys_role" r, "public"."sys_menu" m
WHERE r.role_key = 'student'
  AND m.menu_id IN (2, 202, 203);

-- 3. 创建演示学生账号
--    登录名（学号）2026001，密码 123456（bcrypt 哈希，改密码请重新生成哈希）
--    ⚠️ dept_id=100 是占位符，请改成 sys_dept 里实际的学院 dept_id：
--       SELECT dept_id, dept_name FROM sys_dept WHERE del_flag='0';
INSERT INTO "public"."sys_user"
  ("user_name", "nick_name", "dept_id", "user_type", "password", "status", "del_flag", "create_by", "create_time")
VALUES
  ('2026001', '张三', 100, '00', '$2b$12$MNwMfzlTtq.diTwz6Iv7KuoNarwVDvfwesDxbj1GIvR4k3RHAjHhu', '0', '0', 'admin', now());

-- 4. 把学生账号关联到 student 角色
INSERT INTO "public"."sys_user_role" ("user_id", "role_id")
SELECT u.user_id, r.role_id
FROM "public"."sys_user" u, "public"."sys_role" r
WHERE u.user_name = '2026001' AND r.role_key = 'student';

-- 5. 重置角色主键序列（避免后续通过界面新增角色时主键冲突）
SELECT setval('sys_role_role_id_seq', (SELECT COALESCE(MAX(role_id), 1) FROM sys_role));
