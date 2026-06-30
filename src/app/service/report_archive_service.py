from __future__ import annotations

from src.domain.entity import ReportArchive
from src.infra.repo.mem import MemUnitOfWork


class ReportArchiveService:
    def __init__(self, uow: MemUnitOfWork) -> None:
        self.uow = uow

    def get_by_task(self, task_id: str) -> ReportArchive:
        report = self.uow.reports.get_by_task(task_id)
        if report is None:
            raise ValueError("报告不存在")
        return report
