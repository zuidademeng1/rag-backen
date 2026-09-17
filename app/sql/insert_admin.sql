-- 插入一个 admin 角色（role_key='admin'，登录后 is_admin=True，可跳过所有权限校验）
INSERT INTO "public"."sys_role" ("role_name", "role_key", "role_sort", "data_scope", "status", "del_flag", "create_by", "create_time")
VALUES ('超级管理员', 'admin', 1, '1', '0', '0', 'admin', now());

-- 插入一个 admin 用户（账号 admin，密码 admin123，bcrypt 加密）
INSERT INTO "public"."sys_user" ("user_name", "nick_name", "user_type", "password", "status", "del_flag", "create_by", "create_time")
VALUES ('admin', '管理员', '00', '$2b$12$kP7c5rbaFMpKR1qVvtXlEuGvydG9yaGUkZQhYP2JXVmKGHQCkrKMi', '0', '0', 'admin', now());

-- 把 admin 用户关联到 admin 角色（sys_user_role 中间表）
INSERT INTO "public"."sys_user_role" ("user_id", "role_id")
SELECT u.user_id, r.role_id
FROM "public"."sys_user" u, "public"."sys_role" r
WHERE u.user_name = 'admin' AND r.role_key = 'admin';
