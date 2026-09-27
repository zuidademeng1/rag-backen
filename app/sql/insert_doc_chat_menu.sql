-- 文档管理菜单
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (201, '文档管理', 2, 2, 'doc', 'ai/doc/index', 'Doc', 'C', '0', '0', 'ai:doc:list', 'example', 'admin', now());

-- 对话问答菜单
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (202, '对话问答', 2, 3, 'chat', 'ai/chat/index', 'Chat', 'C', '0', '0', 'ai:chat:talk', 'message', 'admin', now());

SELECT setval('sys_menu_menu_id_seq', (SELECT COALESCE(MAX(menu_id), 1) FROM sys_menu));
