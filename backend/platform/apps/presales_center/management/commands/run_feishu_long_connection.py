from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.presales_center.long_connection import FeishuLongConnectionRunner


class Command(BaseCommand):
    help = "启动飞书 SDK 长连接回调监听，用于处理售前任务卡片交互。"

    def handle(self, *args, **options):
        runner = FeishuLongConnectionRunner()
        try:
            runner.validate()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("飞书长连接监听启动中..."))
        self.stdout.write(self.style.WARNING("保持该进程运行，飞书卡片交互事件将通过 SDK 长连接接收。"))
        runner.run_forever()
