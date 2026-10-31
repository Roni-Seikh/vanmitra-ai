"""QR generation. The QR only encodes a lookup URL; it does not authenticate anything."""
import io
from urllib.parse import quote, urlparse, parse_qs
import qrcode


def batch_url(base_url, batch_id):
    return f"{base_url.rstrip('/')}/?batch={quote(batch_id)}"


def make_qr_png(base_url, batch_id):
    img = qrcode.make(batch_url(base_url, batch_id), box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def batch_id_from_url(url):
    v = parse_qs(urlparse(url).query).get("batch")
    return v[0] if v else None
