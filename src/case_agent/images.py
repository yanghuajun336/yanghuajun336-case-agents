"""Helpers for image metadata handling in case sessions."""

from __future__ import annotations

import uuid

from .models import ImageAttachment


def create_image_attachment(
    file_name: str,
    summary: str,
    mime_type: str = "image/png",
    linked_sections: list[str] | None = None,
    source: str = "cli",
) -> ImageAttachment:
    return ImageAttachment(
        image_id=f"img-{uuid.uuid4().hex[:8]}",
        file_name=file_name,
        summary=summary,
        mime_type=mime_type,
        linked_sections=linked_sections or [],
        source=source,
    )
