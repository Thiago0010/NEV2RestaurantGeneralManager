import qrcode
import base64
from io import BytesIO
from typing import Optional
import secrets


def generate_qr_token(length: int = 32) -> str:
    """Generate a secure random token for QR codes"""
    return secrets.token_urlsafe(length)


def generate_qr_code_image(data: str, size: int = 300) -> str:
    """Generate QR code image as base64 encoded PNG"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize to desired size
    img = img.resize((size, size))
    
    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"


def generate_qr_code_url(base_url: str, qr_token: str) -> str:
    """Generate the public URL for a table's QR code"""
    return f"{base_url.rstrip('/')}/r/qr/{qr_token}"


def parse_qr_url(url: str) -> Optional[dict]:
    """Parse a QR code URL to extract restaurant slug and table number"""
    # Expected format: /r/{slug}/table/{num} or /r/qr/{token}
    import re
    
    # Try token format
    token_match = re.search(r'/r/qr/([a-zA-Z0-9_-]+)', url)
    if token_match:
        return {"type": "token", "token": token_match.group(1)}
    
    # Try slug/table format
    slug_match = re.search(r'/r/([a-zA-Z0-9_-]+)/table/(\d+)', url)
    if slug_match:
        return {"type": "slug_table", "slug": slug_match.group(1), "table_number": slug_match.group(2)}
    
    return None