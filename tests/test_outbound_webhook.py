import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.outbound_webhook import (
    WebhookSecurityError, dispatch_webhook, _sign_payload, validate_webhook_url,
)
from app.services.field_crypto import encrypt_field


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
        wh = OutboundWebhook(company_id=1, url="https://public.example", secret=encrypt_field("sec"), active=True, events="workflow.completed")
        db_session.add(wh)
        db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "ok"

        with patch("app.services.outbound_webhook.validate_webhook_url", return_value=wh.url), \
             patch("app.services.outbound_webhook.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=mock_resp)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            from app.services.outbound_webhook import _send_with_retry
            await _send_with_retry(db_session, wh, "workflow.completed", {"test": True})

        from app.models.outbound_webhook import OutboundWebhookLog
        log = db_session.query(OutboundWebhookLog).filter_by(webhook_id=wh.id).first()
        assert log is not None
        assert log.success is True
        assert log.status_code == 200
        assert log.request_body == ""
        assert log.response_body == ""
        sent_headers = mock_client.return_value.__aenter__.return_value.post.call_args.kwargs["headers"]
        signed_body = json.dumps({"test": True}, default=str, ensure_ascii=False).encode()
        assert sent_headers["X-FlowAI-Signature"] == f"sha256={_sign_payload(signed_body, 'sec')}"

    @pytest.mark.asyncio
    async def test_logs_failure(self, db_session):
        from app.models.outbound_webhook import OutboundWebhook
        wh = OutboundWebhook(company_id=1, url="https://public.example", active=True, events="workflow.completed")
        db_session.add(wh)
        db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"

        with patch("app.services.outbound_webhook.validate_webhook_url", return_value=wh.url), \
             patch("app.services.outbound_webhook.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=mock_resp)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("app.services.outbound_webhook.asyncio.sleep", new=AsyncMock()):
                from app.services.outbound_webhook import _send_with_retry
                await _send_with_retry(db_session, wh, "workflow.completed", {"test": True})

        from app.models.outbound_webhook import OutboundWebhookLog
        log = db_session.query(OutboundWebhookLog).filter_by(webhook_id=wh.id).first()
        assert log is not None
        assert log.success is False
        assert log.status_code == 500


class TestWebhookUrlPolicy:
    @patch("app.services.outbound_webhook.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("8.8.8.8", 443))])
    def test_allows_public_https_and_removes_fragment(self, _dns):
        assert validate_webhook_url("https://hooks.example/x#fragment") == "https://hooks.example/x"

    @pytest.mark.parametrize("url", [
        "http://public.example", "https://127.0.0.1/x", "https://[::1]/",
        "https://169.254.169.254/latest/meta-data", "https://user:pass@example.com",
    ])
    def test_blocks_unsafe_targets(self, url):
        with pytest.raises(WebhookSecurityError):
            validate_webhook_url(url)

    @patch("app.services.outbound_webhook.socket.getaddrinfo", return_value=[
        (2, 1, 6, "", ("8.8.8.8", 443)), (2, 1, 6, "", ("10.0.0.1", 443)),
    ])
    def test_blocks_mixed_public_private_dns(self, _dns):
        with pytest.raises(WebhookSecurityError):
            validate_webhook_url("https://mixed.example/hook")

    @pytest.mark.asyncio
    async def test_blocked_destination_never_opens_client(self, db_session):
        from app.models.outbound_webhook import OutboundWebhook, OutboundWebhookLog
        from app.services.outbound_webhook import _send_with_retry
        wh = OutboundWebhook(company_id=1, url="https://blocked.example", active=True, events="workflow.completed")
        db_session.add(wh)
        db_session.commit()
        with patch("app.services.outbound_webhook.validate_webhook_url", side_effect=WebhookSecurityError()), \
             patch("app.services.outbound_webhook.httpx.AsyncClient") as client:
            await _send_with_retry(db_session, wh, "workflow.completed", {"private": "synthetic"})
            client.assert_not_called()
        log = db_session.query(OutboundWebhookLog).filter_by(webhook_id=wh.id).one()
        assert log.request_body == "" and log.response_body == ""
