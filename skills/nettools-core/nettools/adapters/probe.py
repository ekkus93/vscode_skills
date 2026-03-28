from __future__ import annotations

from abc import abstractmethod

from ..models import PathProbeResult
from .base import AdapterContext, BaseAdapter, ProbeRequest


class ProbeAdapter(BaseAdapter):
    @abstractmethod
    def run_path_probes(
        self,
        *,
        request: ProbeRequest,
        context: AdapterContext | None = None,
    ) -> list[PathProbeResult]:
        raise NotImplementedError
