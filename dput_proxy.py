#!/usr/bin/env python3
"""Run dput with FTP connections tunneled through an HTTP CONNECT proxy."""

import base64
import ftplib
import os
import runpy
import socket
import sys
import urllib.parse
import urllib.request


def _get_proxy_url():
    for var in ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"):
        val = os.environ.get(var)
        if val:
            return val
    return None


def _parse_proxy(proxy_url):
    if "://" not in proxy_url:
        proxy_url = "http://" + proxy_url
    parsed = urllib.parse.urlparse(proxy_url)
    host = parsed.hostname
    port = parsed.port or 3128
    auth_header = None
    if parsed.username is not None:
        user = urllib.parse.unquote(parsed.username)
        password = urllib.parse.unquote(parsed.password or "")
        token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        auth_header = f"Proxy-Authorization: Basic {token}\r\n"
    return host, port, auth_header


def _connect_via_proxy(orig_create_connection, proxy_host, proxy_port, auth_header, address, timeout, source_address):
    target_host, target_port = address[0], address[1]
    sock = orig_create_connection((proxy_host, proxy_port), timeout=timeout, source_address=source_address)
    try:
        req = (
            f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
            f"Host: {target_host}:{target_port}\r\n"
        )
        if auth_header:
            req += auth_header
        req += "\r\n"
        sock.sendall(req.encode("ascii"))

        buf = bytearray()
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(1)
            if not chunk:
                raise OSError(f"Proxy closed connection during CONNECT to {target_host}:{target_port}")
            buf.extend(chunk)
            if len(buf) > 65536:
                raise OSError("Proxy response header too large")

        status_line = buf.split(b"\r\n", 1)[0].decode("latin-1")
        parts = status_line.split(" ", 2)
        if len(parts) < 2 or parts[1] != "200":
            raise OSError(f"Proxy CONNECT to {target_host}:{target_port} failed: {status_line}")
        return sock
    except Exception:
        sock.close()
        raise


def _install_proxy_hooks(proxy_url):
    proxy_host, proxy_port, auth_header = _parse_proxy(proxy_url)
    orig_create_connection = socket.create_connection
    orig_ftp_connect = ftplib.FTP.connect
    orig_ftp_makepasv = ftplib.FTP.makepasv

    def proxied_create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None, **kwargs):
        host = address[0]
        if urllib.request.proxy_bypass(host):
            return orig_create_connection(address, timeout=timeout, source_address=source_address, **kwargs)
        return _connect_via_proxy(
            orig_create_connection,
            proxy_host,
            proxy_port,
            auth_header,
            address,
            timeout,
            source_address,
        )

    def proxied_ftp_connect(self, host="", port=0, timeout=-999, source_address=None):
        if host:
            self._proxy_target_host = host
        return orig_ftp_connect(self, host=host, port=port, timeout=timeout, source_address=source_address)

    def proxied_ftp_makepasv(self):
        host, port = orig_ftp_makepasv(self)
        target_host = getattr(self, "_proxy_target_host", None)
        if target_host:
            return target_host, port
        return host, port

    socket.create_connection = proxied_create_connection
    ftplib.FTP.connect = proxied_ftp_connect
    ftplib.FTP.makepasv = proxied_ftp_makepasv


def main():
    proxy_url = _get_proxy_url()
    if proxy_url:
        _install_proxy_hooks(proxy_url)

    dput_bin = os.path.realpath("/usr/bin/dput")
    sys.path.insert(0, os.path.dirname(dput_bin))
    sys.argv = ["dput"] + sys.argv[1:]
    runpy.run_path(dput_bin, run_name="__main__")


if __name__ == "__main__":
    main()
