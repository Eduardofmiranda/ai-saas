import pytest
from app.services.field_crypto import encrypt_field, decrypt_field


class TestFieldCrypto:
    def test_roundtrip(self):
        plain = "gsk_secret_abc123"
        enc = encrypt_field(plain)
        assert enc is not None
        assert enc.startswith("enc:")
        dec = decrypt_field(enc)
        assert dec == plain

    def test_empty_string(self):
        assert encrypt_field("") == ""
        assert decrypt_field("") == ""

    def test_none(self):
        assert encrypt_field(None) is None
        assert decrypt_field(None) is None

    def test_legacy_plaintext_read(self):
        """Valores legados em texto puro sao lidos sem erro (compatibilidade)."""
        legacy = "sk-plain-old-key"
        assert decrypt_field(legacy) == legacy

    def test_tampered_token_returns_empty(self):
        """Token corrompido nao quebra, retorna string vazia."""
        bad = "enc:invalidtoken=="
        assert decrypt_field(bad) == ""

    def test_different_values_produce_different_ciphertext(self):
        e1 = encrypt_field("chave1")
        e2 = encrypt_field("chave2")
        assert e1 != e2
        assert decrypt_field(e1) == "chave1"
        assert decrypt_field(e2) == "chave2"