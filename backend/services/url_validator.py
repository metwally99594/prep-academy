import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional
import logging

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_HOSTS = {
    'commons.wikimedia.org',
    'upload.wikimedia.org',
    'en.wikipedia.org',
    'de.wikipedia.org',
    'ar.wikipedia.org',
    'api.openverse.org',
    'api.openverse.engineering',
    'cdn.openverse.org',
}

ALLOWED_SCHEMES = {'http', 'https'}

BLOCKED_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
    ipaddress.ip_network('0.0.0.0/8'),
]


def validate_image_url(url: str, allow_dns_lookup: bool = True) -> bool:
    if not url or len(url) > 2048:
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False
    host = (parsed.hostname or '').lower()
    if not host:
        return False
    if host not in ALLOWED_IMAGE_HOSTS:
        allowed_suffixes = ('.wikimedia.org', '.wikipedia.org', '.openverse.org')
        if not any(host.endswith(suffix) for suffix in allowed_suffixes):
            logger.warning(f"Blocked host: {host}")
            return False
    try:
        ipaddress.ip_address(host)
        logger.warning(f"Direct IP access blocked: {host}")
        return False
    except ValueError:
        pass
    if allow_dns_lookup:
        try:
            resolved = socket.gethostbyname(host)
            if any(ipaddress.ip_address(resolved) in n for n in BLOCKED_NETWORKS):
                logger.warning(f"Host {host} resolves to blocked IP {resolved}")
                return False
        except socket.gaierror:
            logger.warning(f"DNS lookup failed for {host}")
            return False
    port = parsed.port
    if port is not None and port not in (80, 443):
        return False
    return True


def normalize_image_url(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        normalized = f"https://{parsed.netloc.lower()}{parsed.path}"
        import re
        normalized = re.sub(r'/\d+px-', '/', normalized)
        normalized = re.sub(r'\?width=\d+', '', normalized)
        return normalized
    except Exception:
        return url
