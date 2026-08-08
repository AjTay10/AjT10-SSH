"""_validate_url is a security boundary: it is what stops `reach web <url>`
from fetching the container's own network on behalf of whoever supplied the
URL — and URLs arrive from untrusted documents, not just from the user.
"""

import http.server
import socketserver
import threading

import pytest

PUBLIC = "https://example.com/page"

REJECTED = [
    pytest.param("http://127.0.0.1/", id="loopback-v4"),
    pytest.param("http://127.1/", id="loopback-short"),
    pytest.param("http://localhost/", id="localhost"),
    pytest.param("http://LOCALHOST/", id="localhost-uppercase"),
    pytest.param("http://localhost./", id="localhost-trailing-dot"),
    pytest.param("http://foo.localhost/", id="localhost-suffix"),
    pytest.param("http://svc.internal/", id="internal-suffix"),
    pytest.param("http://printer.local/", id="local-suffix"),
    pytest.param("http://router.home.arpa/", id="home-arpa"),
    pytest.param("http://10.0.0.5/", id="rfc1918-10"),
    pytest.param("http://192.168.1.1/", id="rfc1918-192"),
    pytest.param("http://172.16.0.1/", id="rfc1918-172"),
    pytest.param("http://169.254.169.254/latest/meta-data/", id="cloud-metadata"),
    pytest.param("http://[::1]/", id="loopback-v6"),
    pytest.param("http://[::ffff:127.0.0.1]/", id="v4-mapped-v6-loopback"),
    pytest.param("http://[fe80::1]/", id="link-local-v6"),
    pytest.param("http://0.0.0.0/", id="unspecified"),
    pytest.param("file:///etc/passwd", id="file-scheme"),
    pytest.param("ftp://example.com/", id="ftp-scheme"),
    pytest.param("gopher://example.com/", id="gopher-scheme"),
    pytest.param("http://user:pw@example.com/", id="embedded-credentials"),
    pytest.param("http://example.com/\nHost: evil", id="crlf-injection"),
    pytest.param("", id="empty"),
    pytest.param("   ", id="whitespace-only"),
    pytest.param("not a url", id="not-a-url"),
    pytest.param("http:///nohost", id="no-host"),
]


@pytest.mark.parametrize("url", REJECTED)
def test_rejects_non_public_urls(reach, url):
    with pytest.raises(reach.ReachError):
        reach._validate_url(url)


@pytest.mark.parametrize("url", [
    "https://example.com",
    "https://example.com/a/b?c=d#e",
    "http://example.com:8080/x",
])
def test_accepts_public_urls(reach, url):
    assert reach._validate_url(url) == url


def test_strips_surrounding_whitespace(reach):
    assert reach._validate_url("  https://example.com  ") == "https://example.com"


def test_rejects_non_string(reach):
    with pytest.raises(reach.ReachError):
        reach._validate_url(None)


def test_unresolvable_host_is_an_error_not_a_pass(reach):
    with pytest.raises(reach.ReachError) as e:
        reach._validate_url("https://no-such-host.invalid/")
    assert "resolve" in str(e.value)


# --------------------------------------------------------------- redirects
# Regression test. _validate_url only ever saw the URL the caller passed, while
# urllib followed 3xx with the default opener — so a public host answering
# "302 -> http://169.254.169.254/" walked straight into the private network.


class _Redirector(http.server.BaseHTTPRequestHandler):
    target = ""

    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", self.target)
            self.end_headers()
        else:
            body = b"INTERNAL-ONLY-CONTENT"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture
def redirector():
    srv = socketserver.TCPServer(("127.0.0.1", 0), _Redirector)
    port = srv.server_address[1]
    _Redirector.target = f"http://127.0.0.1:{port}/internal"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()
    srv.server_close()


def test_redirect_into_private_space_is_blocked(reach, redirector):
    with pytest.raises(reach.ReachError) as e:
        reach.http(f"{redirector}/redirect", accept_errors=True)
    assert "public" in str(e.value)


def test_blocked_redirect_does_not_leak_the_body(reach, redirector):
    try:
        _, body = reach.http(f"{redirector}/redirect", accept_errors=True)
    except reach.ReachError:
        return
    assert b"INTERNAL-ONLY-CONTENT" not in body, "redirect guard was bypassed"


def test_redirect_guard_reraises_reacherror_unwrapped(reach, redirector):
    """http()'s generic `except Exception` would otherwise rewrite the guard's
    message into a vague transport error and hide why the fetch stopped."""
    with pytest.raises(reach.ReachError) as e:
        reach.http(f"{redirector}/redirect", accept_errors=True)
    assert "reaching" not in str(e.value)


def test_redirect_handler_is_installed_on_the_opener(reach):
    opener = reach._opener()
    assert any(isinstance(h, reach._GuardedRedirectHandler) for h in opener.handlers)
