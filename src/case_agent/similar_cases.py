"""Similar-case recommendation interfaces and stubs."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .models import SimilarCaseHit


class SimilarCaseRecommender(Protocol):
    """Pluggable interface for future memory-rag/hello-agent retrieval."""

    def recommend(self, problem_text: str, image_summaries: list[str], top_k: int = 3) -> list[SimilarCaseHit]:
        ...


class MockSimilarCaseRecommender:
    """Mock implementation used by MVP workflow and CLI demo."""

    CONTEXT_BONUS = 0.02
    MAX_SCORE = 0.99

    _seed_hits = [
        SimilarCaseHit(
            case_id="case-ssh-vrf-001",
            title="VRF 场景下 SSH 无法访问 loopback",
            score=0.92,
            summary="连接失败且仅默认路由可达，需检查 VRF 绑定与监听地址。",
            root_cause="socket 未绑定 VRF 设备",
            solution="补充 SO_BINDTODEVICE 并校验 VRF 路由",
            tags=["ssh", "vrf", "network"],
        ),
        SimilarCaseHit(
            case_id="case-sshd-addr-014",
            title="sshd 未监听目标地址",
            score=0.86,
            summary="sshd 配置 ListenAddress 缺失导致目标地址不可达。",
            root_cause="sshd 配置不完整",
            solution="补充 ListenAddress 并重载服务",
            tags=["ssh", "config"],
        ),
        SimilarCaseHit(
            case_id="case-auth-timeout-032",
            title="认证链路超时导致登录失败",
            score=0.79,
            summary="认证服务超时触发连接中断，表现为偶发失败。",
            root_cause="依赖服务响应慢",
            solution="优化认证依赖或增加重试",
            tags=["auth", "timeout"],
        ),
    ]

    def recommend(self, problem_text: str, image_summaries: list[str], top_k: int = 3) -> list[SimilarCaseHit]:
        context_bonus = self.CONTEXT_BONUS if image_summaries else 0.0
        hits = [replace(hit, score=min(hit.score + context_bonus, self.MAX_SCORE)) for hit in self._seed_hits[:top_k]]
        return sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]
