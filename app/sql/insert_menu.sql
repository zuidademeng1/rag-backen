-- ----------------------------
-- 初始化菜单数据（RuoYi-Vue3 前端适配）
-- 说明：
--   menu_type: M=目录 C=菜单 F=按钮
--   本脚本只插目录(M)和菜单(C)，按钮(F)权限由 admin 的 is_admin 绕过，无需写入
--   组件路径 component 对应前端 src/views/ 下的 .vue 文件
-- ----------------------------

-- 目录：系统管理
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (1, '系统管理', 0, 1, 'system', NULL, '', 'M', '0', '0', NULL, 'system', 'admin', now());

-- 菜单：用户管理
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (100, '用户管理', 1, 1, 'user', 'system/user/index', 'User', 'C', '0', '0', 'system:user:list', 'user', 'admin', now());

-- 菜单：角色管理
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (101, '角色管理', 1, 2, 'role', 'system/role/index', 'Role', 'C', '0', '0', 'system:role:list', 'peoples', 'admin', now());

-- 菜单：菜单管理
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (102, '菜单管理', 1, 3, 'menu', 'system/menu/index', 'Menu', 'C', '0', '0', 'system:menu:list', 'tree-table', 'admin', now());

-- 菜单：部门管理
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (103, '部门管理', 1, 4, 'dept', 'system/dept/index', 'Dept', 'C', '0', '0', 'system:dept:list', 'tree', 'admin', now());

-- 菜单：字典管理
INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, route_name, menu_type, visible, status, perms, icon, create_by, create_time)
VALUES (104, '字典管理', 1, 5, 'dict', 'system/dict/index', 'Dict', 'C', '0', '0', 'system:dict:list', 'dict', 'admin', now());

-- 重置菜单主键序列，避免后续通过界面新增菜单时主键冲突
SELECT setval('sys_menu_menu_id_seq', (SELECT COALESCE(MAX(menu_id), 1) FROM sys_menu));
