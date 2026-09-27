-- ----------------------------
-- AI 模块菜单（知识库 / 文档 / 对话）
-- ----------------------------

-- 目录：AI助手
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (2, 'AI助手', 0, 2, 'ai', NULL, 'Ai', 'M', '0', '0', NULL, 'monitor', 'admin', now());

-- 菜单：知识库管理
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (200, '知识库管理', 2, 1, 'kb', 'ai/kb/index', 'Kb', 'C', '0', '0', 'ai:kb:list', 'documentation', 'admin', now());

-- 重置菜单主键序列
SELECT setval('sys_menu_menu_id_seq', (SELECT COALESCE(MAX(menu_id), 1) FROM sys_menu));
