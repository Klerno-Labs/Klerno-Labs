import pytest

from app.crypto_iso20022_integration import CryptoISO20022Manager, SupportedCryptos


def test_crypto_generate_payment_happy():
    mgr = CryptoISO20022Manager()
    payload = mgr.generate_crypto_payment_message(
        crypto=SupportedCryptos.XRP,
        amount=1.0,
        sender_info={"name": "Alice"},
        recipient_info={"name": "Bob"},
    )
    assert payload["cryptocurrency"] == "XRP"
    assert payload["network"] == "xrpl"
    assert payload["amount"]["currency"] == "XRP"
    assert float(payload["amount"]["value"]) == 1.0


def test_crypto_generate_payment_below_min_raises():
    mgr = CryptoISO20022Manager()
    with pytest.raises(ValueError):
        mgr.generate_crypto_payment_message(
            crypto=SupportedCryptos.XRP,
            amount=0.0000001,  # below 1 drop (1e - 6)
            sender_info={"name": "Alice"},
            recipient_info={"name": "Bob"},
        )


def test_get_all_supported_cryptos_contains_xrp():
    mgr = CryptoISO20022Manager()
    allc = mgr.get_all_supported_cryptos()
    assert "XRP" in allc
    assert allc["XRP"]["iso20022_compliant"] is True
