-- ============================================================
-- 初始化字典数据（用户管理/角色管理下拉框需要）
-- 只跑一次；若字典类型已存在会重复，届时删掉重跑即可
-- ============================================================

-- 字典类型
INSERT INTO sys_dict_type (dict_name, dict_type, status, create_by, create_time)
VALUES ('用户性别', 'sys_user_sex', '0', 'admin', now()),
       ('系统开关', 'sys_normal_disable', '0', 'admin', now());

-- 字典数据
INSERT INTO sys_dict_data (dict_sort, dict_label, dict_value, dict_type, is_default, status, create_by, create_time)
VALUES
  (1, '男',   '0', 'sys_user_sex',      'Y', '0', 'admin', now()),
  (2, '女',   '1', 'sys_user_sex',      'N', '0', 'admin', now()),
  (3, '未知', '2', 'sys_user_sex',      'N', '0', 'admin', now()),
  (1, '正常', '0', 'sys_normal_disable', 'Y', '0', 'admin', now()),
  (2, '停用', '1', 'sys_normal_disable', 'N', '0', 'admin', now());
