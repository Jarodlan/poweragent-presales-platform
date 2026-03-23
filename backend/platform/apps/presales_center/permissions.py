from __future__ import annotations

from apps.accounts.permissions import HasPermissionCode


class CanAccessPresalesCenter(HasPermissionCode):
    permission_code = "presales_center.access"


class CanViewPresalesTask(HasPermissionCode):
    permission_code = "presales_task.view"


class CanManagePresalesTask(HasPermissionCode):
    permission_code = "presales_task.manage"


class CanViewPresalesArchive(HasPermissionCode):
    permission_code = "presales_archive.view"


class CanManagePresalesArchive(HasPermissionCode):
    permission_code = "presales_archive.manage"


class CanViewFeishuDelivery(HasPermissionCode):
    permission_code = "feishu_delivery.view"


class CanManageFeishuDelivery(HasPermissionCode):
    permission_code = "feishu_delivery.manage"


class CanManageFeishuSync(HasPermissionCode):
    permission_code = "feishu_sync.manage"
