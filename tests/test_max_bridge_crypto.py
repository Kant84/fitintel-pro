# tests/test_max_bridge_crypto.py
"""MAX Bridge: криптопроверка initData (HMAC WebAppData) — без БД."""
import hashlib, hmac, json, time, urllib.parse

from app.api.v1.miniapp_config import _validate_init

BOT_TOKEN = "test-bot-token-123"


def _mk_init(user_id=38455196, name="Андрей", auth_date=None, tamper=False):
    auth_date = auth_date or int(time.time())
    data = {"auth_date": str(auth_date),
            "user": json.dumps({"id": user_id, "first_name": name}, ensure_ascii=False),
            "query": "x=1"}
    pairs = sorted("%s=%s" % (k, urllib.parse.quote(str(v), safe="")) for k, v in data.items())
    dec = {k: urllib.parse.unquote(v) for k, v in (p.split("=", 1) for p in pairs)}
    check = "\n".join("%s=%s" % (k, dec[k]) for k in sorted(dec))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    sig = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    init = "&".join(pairs + ["hash=" + sig])
    if tamper:  # взлом: подпись по чистым данным, лишнее поле — после
        init = init.replace("&hash=", "&extra=evil&hash=")
    return init


class TestValidateInit:
    def test_valid_returns_user(self):
        u = _validate_init(_mk_init(), BOT_TOKEN)
        assert u and u["id"] == 38455196 and u["first_name"] == "Андрей"

    def test_tampered_data_rejected(self):
        assert _validate_init(_mk_init(tamper=True), BOT_TOKEN) is None

    def test_wrong_bot_token_rejected(self):
        assert _validate_init(_mk_init(), "other-token") is None

    def test_stale_auth_date_rejected(self):
        old = _mk_init(auth_date=int(time.time()) - 7200)
        assert _validate_init(old, BOT_TOKEN) is None

    def test_missing_hash_rejected(self):
        assert _validate_init("a=1&b=2", BOT_TOKEN) is None
