"""``GET /events``: Server-Sent Events stream of board and notification changes."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..events import broker
from ..security import require_token

router = APIRouter(tags=["events"], dependencies=[Depends(require_token)])

KEEPALIVE_SECONDS = 15


async def _stream() -> AsyncIterator[str]:
    queue = broker.subscribe()
    try:
        yield ": connected\n\n"
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
    finally:
        broker.unsubscribe(queue)


@router.get("/events")
async def events() -> StreamingResponse:
    """Stream events (task_created, task_moved, task_assigned, comment_added,
    notification_created). Events carry ids and status only. Requires the service token.
    """
    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
