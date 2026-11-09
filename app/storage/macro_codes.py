import json, base64, zlib

PREFIX = "PMM:"


def encode_macro(macro):
    try:
        data = macro.to_dict() if hasattr(macro, "to_dict") else macro
        j = json.dumps(data, separators=(",",":"), ensure_ascii=False)
        payload = zlib.compress(j.encode("utf-8"))
        code = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        return PREFIX + code
    except Exception:
        return ""


def decode_macro_code(code):
    try:
        text = str(code or "").strip()
        if not text:
            return None
        if text.upper().startswith(PREFIX):
            text = text[len(PREFIX):]
        pad = "=" * (-len(text) % 4)
        raw = base64.urlsafe_b64decode(text + pad)
        try:
            decoded = zlib.decompress(raw).decode("utf-8")
        except zlib.error:
            decoded = raw.decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return None
