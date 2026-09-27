-- ============================================================
-- 文件浏览菜单（学生可浏览公共库文档原件）
-- 依赖：菜单 2（AI助手目录）已存在；本文件需在 insert_student_role.sql 之前执行
-- ============================================================

INSERT INTO "public"."sys_menu"
  ("menu_id", "menu_name", "parent_id", "order_num", "path", "component", "route_name", "menu_type", "visible", "status", "perms", "icon", "create_by", "create_time")
VALUES
  (203, '文件浏览', 2, 4, 'browse', 'ai/browse/index', 'Browse', 'C', '0', '0', NULL, 'folder', 'admin', now());

-- 分配给 student 角色
INSERT INTO "public"."sys_role_menu" ("role_id", "menu_id")
SELECT r.role_id, m.menu_id
FROM "public"."sys_role" r, "public"."sys_menu" m
WHERE r.role_key = 'student' AND m.menu_id = 203;

SELECT setval('sys_menu_menu_id_seq', (SELECT COALESCE(MAX(menu_id), 1) FROM sys_menu));
