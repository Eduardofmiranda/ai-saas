from types import SimpleNamespace

from app.models.campaign import Campaign, CampaignLog
from app.models.customer import Customer
from app.routers.campaign_router import CampaignCreate, create_campaign, router
from app.services.deps import require_company_manager
from app.tasks import campaign_tasks
from app.tasks.celery_app import celery_app


def _campaign(db, company_id: int, total: int) -> Campaign:
    campaign = Campaign(
        company_id=company_id,
        name="Oferta",
        message="Mensagem de teste",
        status="pending",
        total_recipients=total,
    )
    db.add(campaign)
    db.flush()
    for index in range(total):
        db.add(CampaignLog(campaign_id=campaign.id, phone=f"5511999999{index:03d}"))
    db.commit()
    return campaign


def _configure_task(monkeypatch, db_session):
    monkeypatch.setattr(campaign_tasks, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(campaign_tasks, "get_or_create_config", lambda _db, _company_id: object())
    monkeypatch.setattr(campaign_tasks, "_evo_config", lambda _config: ("http://evolution", "test-key", "inst-1"))
    monkeypatch.setattr(campaign_tasks.time, "sleep", lambda _seconds: None)


def test_campaign_task_processes_a_bounded_batch_and_schedules_next(monkeypatch, db_session, company):
    campaign = _campaign(db_session, company.id, campaign_tasks.BATCH_SIZE + 1)
    campaign_id = campaign.id
    _configure_task(monkeypatch, db_session)
    sent_to = []
    scheduled = []

    async def fake_send_text(**kwargs):
        sent_to.append(kwargs["to_phone"])
        return {"ok": True}

    monkeypatch.setattr(campaign_tasks.evolution, "send_text", fake_send_text)
    monkeypatch.setattr(
        campaign_tasks.send_campaign,
        "apply_async",
        lambda *args, **kwargs: scheduled.append((args, kwargs)),
    )

    result = campaign_tasks.send_campaign.run(campaign_id)

    assert result == {"status": "scheduled", "processed": campaign_tasks.BATCH_SIZE}
    assert len(sent_to) == campaign_tasks.BATCH_SIZE
    assert scheduled == [((), {"args": (campaign_id,), "countdown": campaign_tasks.SEND_DELAY_SECONDS})]
    assert db_session.query(CampaignLog).filter(CampaignLog.status == "sent").count() == campaign_tasks.BATCH_SIZE
    assert db_session.query(CampaignLog).filter(CampaignLog.status == "pending").count() == 1
    assert db_session.get(Campaign, campaign_id).status == "sending"


def test_campaign_task_sanitizes_evolution_errors(monkeypatch, db_session, company):
    campaign = _campaign(db_session, company.id, 1)
    campaign_id = campaign.id
    _configure_task(monkeypatch, db_session)

    async def fake_send_text(**_kwargs):
        raise RuntimeError("apikey=secret-value and remote payload")

    monkeypatch.setattr(campaign_tasks.evolution, "send_text", fake_send_text)

    result = campaign_tasks.send_campaign.run(campaign_id)

    log = db_session.query(CampaignLog).filter(CampaignLog.campaign_id == campaign_id).one()
    refreshed = db_session.get(Campaign, campaign_id)
    assert result == {"status": "completed", "processed": 1}
    assert log.status == "error"
    assert log.error == campaign_tasks.GENERIC_DELIVERY_ERROR
    assert "secret-value" not in log.error
    assert refreshed.status == "completed"
    assert refreshed.sent_count == 0
    assert refreshed.error_count == 1


def test_campaign_tasks_are_registered_for_worker_and_recovery():
    assert "app.tasks.campaign_tasks" in celery_app.conf.include
    assert celery_app.conf.beat_schedule["campaign-recover-pending-every-5min"]["task"] == (
        "app.tasks.campaign_tasks.recover_pending_campaigns"
    )


def test_campaign_routes_require_manager_access():
    campaign_routes = [route for route in router.routes if getattr(route, "path", "").startswith("/campaigns")]
    assert campaign_routes
    for route in campaign_routes:
        assert route.dependant.dependencies[0].call is require_company_manager


def test_create_campaign_deduplicates_recipient_phones(db_session, company):
    first = Customer(company_id=company.id, phone="(11) 99999-9999", name="Primeiro")
    second = Customer(company_id=company.id, phone="11999999999", name="Segundo")
    db_session.add_all([first, second])
    db_session.commit()
    actor = SimpleNamespace(company_id=company.id, id=1)

    campaign = create_campaign(
        CampaignCreate(name="  Oferta  ", message="  Oi  ", customer_ids=[first.id, second.id]),
        actor,
        db_session,
    )

    assert campaign.name == "Oferta"
    assert campaign.message == "Oi"
    assert campaign.total_recipients == 1
    assert db_session.query(CampaignLog).filter(CampaignLog.campaign_id == campaign.id).count() == 1
