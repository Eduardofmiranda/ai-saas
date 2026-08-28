import pytest
from app.services.config_service import get_or_create_config, get_config
from app.services.field_crypto import decrypt_field


class TestConfigService:
    def test_get_or_create_creates_defaults(self, db_session, company):
        cfg = get_or_create_config(db_session, company.id)
        assert cfg.company_id == company.id
        assert cfg.ai_provider == ""
        assert cfg.ai_on is True

    def test_get_config_returns_none_if_missing(self, db_session, company):
        # nao cria, so busca
        assert get_config(db_session, company.id) is None

    def test_update_encrypts_sensitive_fields(self, db_session, company, config):
        from app.services.field_crypto import encrypt_field
        # Simula o que o router faz
        config.ai_api_key = encrypt_field("gsk_NOVA_CHAVE")
        config.evolution_api_key = encrypt_field("evo_NOVA")
        db_session.commit()
        db_session.refresh(config)

        # Lidos do banco, estao criptografados
        assert config.ai_api_key.startswith("enc:")
        assert config.evolution_api_key.startswith("enc:")

        # Descriptografa corretamente
        assert decrypt_field(config.ai_api_key) == "gsk_NOVA_CHAVE"
        assert decrypt_field(config.evolution_api_key) == "evo_NOVA"

    def test_legacy_plaintext_keys_still_readable(self, db_session, company, config):
        # Simula chave legada em texto puro
        config.ai_api_key = "sk_legada_sem_enc"
        config.evolution_api_key = "evo_legada"
        db_session.commit()
        db_session.refresh(config)

        assert decrypt_field(config.ai_api_key) == "sk_legada_sem_enc"
        assert decrypt_field(config.evolution_api_key) == "evo_legada"

    def test_empty_keys_not_encrypted(self, db_session, config):
        from app.services.field_crypto import encrypt_field
        config.ai_api_key = encrypt_field("")
        config.evolution_api_key = encrypt_field(None)
        db_session.commit()
        db_session.refresh(config)

        assert config.ai_api_key == ""
        assert config.evolution_api_key is None