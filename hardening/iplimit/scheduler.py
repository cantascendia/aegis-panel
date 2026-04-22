"""APScheduler integration for the IP limiter."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from hardening.iplimit.config import IPLIMIT_POLL_INTERVAL
from hardening.iplimit.task import run_iplimit_poll

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def install_iplimit_scheduler(app: FastAPI) -> None:
    """Install the IP limiter scheduler without editing app/tasks.

    The upstream app uses a custom FastAPI lifespan. Starlette startup
    handlers are not reliable in that shape, so we wrap the existing
    lifespan context and start a small feature-owned scheduler inside it.
    """

    if getattr(app.state, "iplimit_scheduler_installed", False):
        return

    original_lifespan = app.router.lifespan_context
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_iplimit_poll,
        "interval",
        seconds=IPLIMIT_POLL_INTERVAL,
        coalesce=True,
        max_instances=1,
        id="aegis-iplimit-poll",
        replace_existing=True,
    )

    @asynccontextmanager
    async def lifespan_with_iplimit(app_: FastAPI):
        async with original_lifespan(app_):
            scheduler.start()
            logger.info(
                "iplimit scheduler started interval=%ss",
                IPLIMIT_POLL_INTERVAL,
            )
            try:
                yield
            finally:
                scheduler.shutdown(wait=False)
                logger.info("iplimit scheduler stopped")

    app.router.lifespan_context = lifespan_with_iplimit
    app.state.iplimit_scheduler = scheduler
    app.state.iplimit_scheduler_installed = True
