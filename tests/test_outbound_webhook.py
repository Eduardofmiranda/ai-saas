import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.outbound_webhook import dispatch_webhook, _sign_payload


class TestSignPayload:
    def test_returns_sha256_hex(self):
        sig = _sign_payload(b"hello", "secret123")
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_different_inputs_different_sigs(self):
        sig1 = _sign_payload(b"hello", "secret")
        sig2 = _sign_payload(b"world", "secret")
        assert sig1 != sig2

    def test_different_secrets_different_sigs(self):
        sig1 = _sign_payload(b"hello", "secret1")
        sig2 = _sign_payload(b"hello", "secret2")
        assert sig1 != sig2


class TestDispatchWebhook:
    @pytest.mark.asyncio
    async def test_no_webhooks_does_nothing(self, db_session):
        await dispatch_webhook(db_session, company_id=999, event="workflow.completed", payload={"test": True})

    @pytest.mark.asyncio
    async def test_skips_inactive_webhooks(self, db_session):
        from app.models.outbound_webhook import OutboundWebhook
        wh = OutboundWebhook(company_id=1, url="http://test.com", active=False, events="workflow.completed")
        db_session.add(wh)
        db_session.commit()

        with patch("app.services.outbound_webhook._send_with_retry") as mock_send:
            await dispatch_webhook(db_session, company_id=1, event="workflow.completed", payload={})
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_non_matching_events(self, db_session):
        from app.models.outbound_webhook import OutboundWebhook
        wh = OutboundWebhook(company_id=1, url="http://test.com", active=True, events="workflow.completed")
        db_session.add(wh)
        db_session.commit()

        with patch("app.services.outbound_webhook._send_with_retry") as mock_send:
            await dispatch_webhook(db_session, company_id=1, event="workflow.error", payload={})
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_send_for_matching_events(self, db_session):
        from app.models.outbound_webhook import OutboundWebhook
        wh = OutboundWebhook(company_id=1, url="http://test.com", active=True, events="workflow.completed,workflow.error")
        db_session.add(wh)
        db_session.commit()

        with patch("app.services.outbound_webhook._send_with_retry") as mock_send:
            mock_send.return_value = None
            await dispatch_webhook(db_session, company_id=1, event="workflow.completed", payload={"test": True})
            mock_send.assert_called_once()


class TestSendWithRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self, db_session):
        from app.models.outbound_webhook import OutboundWebhook
        wh = OutboundWebhook(company_id=1, url="http://test.com", secret="sec", active=True, events="workflow.completed")
        db_session.add(wh)
        db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"

        with patch("app.services.outbound_webhook.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=mock_resp)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            from app.services.outbound_webhook import _send_with_retry
            await _send_with_retry(db_session, wh, "workflow.completed", '{"test":true}')

        from app.models.outbound_webhook import OutboundWebhookLog
        log = db_session.query(OutboundWebhookLog).filter_by(webhook_id=wh.id).first()
        assert log is not None
        assert log.success is True
        assert log.status_code == 200

    @pytest.mark.asyncio
    async def test_logs_failure(self, db_session):
        from app.models.outbound_webhook import OutboundWebhook
        wh = OutboundWebhook(company_id=1, url="http://test.com", active=True, events="workflow.completed")
        db_session.add(wh)
        db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"

        with patch("app.services.outbound_webhook.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=mock_resp)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("app.services.outbound_webhook.time.sleep"):
                from app.services.outbound_webhook import _send_with_retry
                await _send_with_retry(db_session, wh, "workflow.completed", '{"test":true}')

        from app.models.outbound_webhook import OutboundWebhookLog
        log = db_session.query(OutboundWebhookLog).filter_by(webhook_id=wh.id).first()
        assert log is not None
        assert log.success is False
        assert log.status_code == 500
