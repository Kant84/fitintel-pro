# -*- coding: utf-8 -*-
"""П1: периодический опрос support-ящика (IMAP)."""
from celery_app import celery_app


@celery_app.task(name="app.tasks.poll_support_mail")
def poll_support_mail():
    from app.api.v1.support import poll_once
    return poll_once()