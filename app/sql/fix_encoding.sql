-- 修复 cmd(GBK) 执行 insert_student_role.sql 导致的中文乱码
UPDATE sys_role SET role_name='学生' WHERE role_key='student';
UPDATE sys_user SET nick_name='张三' WHERE user_name='2026001';
