"""系统管理模块 API：用户 / 角色 / 权限 / 部门 / 员工 / 审计日志。"""
from api.base import BaseApi


class SystemApi(BaseApi):
    # ---------- 用户 ----------

    def list_users(self, **params):
        """GET /api/system/users"""
        return self._get("/api/system/users", params=params or None)

    def create_user(self, body: dict):
        """POST /api/system/users"""
        return self._post("/api/system/users", json=body)

    def update_user(self, user_id: int, body: dict):
        """PUT /api/system/users/{user_id}"""
        return self._put(f"/api/system/users/{user_id}", json=body)

    def delete_user(self, user_id: int):
        """DELETE /api/system/users/{user_id}"""
        return self._delete(f"/api/system/users/{user_id}")

    def toggle_user_active(self, user_id: int):
        """POST /api/system/users/{user_id}/toggle-active（启用/禁用）"""
        return self._post(f"/api/system/users/{user_id}/toggle-active")

    # ---------- 角色 ----------

    def list_roles(self, **params):
        """GET /api/system/roles"""
        return self._get("/api/system/roles", params=params or None)

    def create_role(self, body: dict):
        """POST /api/system/roles"""
        return self._post("/api/system/roles", json=body)

    def list_permissions(self):
        """GET /api/system/permissions（全部权限点，分组返回）"""
        return self._get("/api/system/permissions")

    def update_role(self, role_id: int, body: dict):
        """PUT /api/system/roles/{role_id}"""
        return self._put(f"/api/system/roles/{role_id}", json=body)

    def delete_role(self, role_id: int):
        """DELETE /api/system/roles/{role_id}"""
        return self._delete(f"/api/system/roles/{role_id}")

    # ---------- 部门 ----------

    def list_departments(self, **params):
        """GET /api/system/departments"""
        return self._get("/api/system/departments", params=params or None)

    def create_department(self, body: dict):
        """POST /api/system/departments"""
        return self._post("/api/system/departments", json=body)

    def update_department(self, dept_id: int, body: dict):
        """PUT /api/system/departments/{dept_id}"""
        return self._put(f"/api/system/departments/{dept_id}", json=body)

    def delete_department(self, dept_id: int):
        """DELETE /api/system/departments/{dept_id}"""
        return self._delete(f"/api/system/departments/{dept_id}")

    # ---------- 员工 ----------

    def list_employees(self, **params):
        """GET /api/system/employees"""
        return self._get("/api/system/employees", params=params or None)

    def create_employee(self, body: dict):
        """POST /api/system/employees"""
        return self._post("/api/system/employees", json=body)

    def update_employee(self, emp_id: int, body: dict):
        """PUT /api/system/employees/{emp_id}"""
        return self._put(f"/api/system/employees/{emp_id}", json=body)

    def delete_employee(self, emp_id: int):
        """DELETE /api/system/employees/{emp_id}"""
        return self._delete(f"/api/system/employees/{emp_id}")

    # ---------- 审计日志 ----------

    def list_audit_logs(self, **params):
        """GET /api/system/audit-logs（keyword/action/page/page_size）"""
        return self._get("/api/system/audit-logs", params=params or None)