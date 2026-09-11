"""Network identity of a ZTNA visitor — IP/MAC enrichment for the admin alert.

Two TCP/IP facts bound what this module can honestly report:

* The server only ever sees the connection's source address. A browser that
  opens ``http://127.0.0.1:8000`` *is* 127.0.0.1 as far as the server can
  tell — its LAN address becomes visible only when the client connects
  through it (``runserver 0.0.0.0`` + ``http://192.168.x.x:8000``), or on
  Render when ``TRUST_X_FORWARDED_FOR`` resolves the proxy chain.
* MAC addresses do not cross routers. A MAC is knowable only when
  (a) the client app volunteers one (``X-MAC-ADDRESS``, the Android app),
  (b) the server shares the visitor's LAN (ARP lookup — dev machine case),
  or (c) the visitor is the server's own machine (loopback → server NIC).

Every value carries its source so the admin alert never shows a guess as
if it were a measurement.
"""
import ipaddress
import logging
import re
import socket
import subprocess
import uuid

from django.core.cache import cache

logger = logging.getLogger('security')

_MAC_RE = re.compile(
    r'\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'
)
_IPV4_RE = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')

ARP_POSITIVE_TTL = 300
ARP_NEGATIVE_TTL = 60

MAC_SOURCE_LABELS = {
    'header': 'مُرسل من تطبيق الجهاز',
    'arp': 'مُطابق من ARP (نفس الشبكة المحلية)',
    'self': 'جهاز الخادم نفسه (طلب محلي)',
    'unknown': '',
}


def _fmt_mac(node: int) -> str:
    return '-'.join(f'{(node >> shift) & 0xFF:02X}' for shift in range(40, -1, -8))


def _run(cmd, timeout=4):
    """Run a helper command without a console window flash on Windows."""
    kwargs = {}
    if hasattr(subprocess, 'CREATE_NO_WINDOW'):
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, **kwargs,
        ).stdout or ''
    except Exception as e:
        logger.debug(f"netinfo: {cmd[0]} failed: {e}")
        return ''


def _arp_table_scan(ip: str) -> str:
    """Parse the system ARP table for `ip`; returns '' when absent."""
    if hasattr(subprocess, 'CREATE_NO_WINDOW'):  # Windows
        out = _run(['arp', '-a'])
        for line in out.splitlines():
            if line.strip().startswith(ip):
                m = _MAC_RE.search(line)
                if m:
                    return m.group(1).upper().replace(':', '-')
    else:  # Linux / macOS
        out = _run(['ip', 'neigh', 'show', ip]) or _run(['arp', '-n', ip])
        for line in out.splitlines():
            if line.startswith(ip) or f' {ip} ' in f' {line} ':
                m = _MAC_RE.search(line)
                if m:
                    return m.group(1).upper().replace(':', '-')
    return ''


def arp_lookup(ip: str, ping_first: bool = False) -> str:
    """MAC of `ip` from the ARP table — only meaningful on a shared LAN.

    ARP entries expire; `ping_first` nudges one into existence with a single
    short probe before reading the table. Results are cached: a positive for
    five minutes, a negative for one.
    """
    key = f'ztna_arp:{ip}'
    cached = cache.get(key)
    if cached is not None:
        return cached

    if ping_first:
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            _run(['ping', '-n', '1', '-w', '600', ip], timeout=3)
        else:
            _run(['ping', '-c', '1', '-W', '1', ip], timeout=3)

    mac = _arp_table_scan(ip)
    cache.set(key, mac, timeout=ARP_POSITIVE_TTL if mac else ARP_NEGATIVE_TTL)
    return mac


def self_mac() -> str:
    """The server machine's own NIC MAC, or '' when only a random one exists.

    ``uuid.getnode`` falls back to a random number on failure and marks it by
    setting the multicast bit — that fallback must not masquerade as hardware.
    """
    node = uuid.getnode()
    if (node >> 40) & 1:
        return ''
    return _fmt_mac(node)


def server_lan_ips():
    """This machine's LAN IPv4 addresses (no traffic is sent).

    The primary address comes from a connected UDP socket (connect() on a
    UDP socket only picks a route — nothing leaves the host). The full list
    comes from name resolution, minus loopback and link-local entries.
    """
    ips = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            primary = s.getsockname()[0]
        if primary and not primary.startswith('127.'):
            ips.append(primary)
    except OSError as e:
        logger.debug(f'netinfo: primary LAN probe failed: {e}')

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith(('127.', '169.254.')) and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


def peer_profile(request) -> dict:
    """Everything the ZTNA alert can honestly say about the visitor."""
    from apps.core.net import get_client_ip

    ip = get_client_ip(request)
    try:
        ip_obj = ipaddress.ip_address(ip)
        is_loopback = ip_obj.is_loopback
        is_private = ip_obj.is_private
    except ValueError:
        is_loopback, is_private = False, False

    mac, mac_source = '', 'unknown'
    header_mac = (request.META.get('HTTP_X_MAC_ADDRESS') or '').strip()
    if header_mac:
        mac, mac_source = header_mac.upper(), 'header'
    elif is_loopback:
        # Same machine: the visitor's MAC *is* the server's NIC MAC.
        mac = self_mac()
        mac_source = 'self' if mac else 'unknown'
    elif is_private:
        mac = arp_lookup(ip, ping_first=True)
        mac_source = 'arp' if mac else 'unknown'

    return {
        'ip': ip,
        'is_loopback': is_loopback,
        'is_private': is_private,
        'mac': mac,
        'mac_source': mac_source,
        'mac_note': MAC_SOURCE_LABELS.get(mac_source, ''),
        'lan_hint': ', '.join(server_lan_ips()) if is_loopback else '',
        'platform': (request.META.get('HTTP_SEC_CH_UA_PLATFORM') or '').strip().strip('"'),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
    }
