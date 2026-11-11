"""Probe the Gunicorn HTTP endpoint over the instance's loopback listener."""

import os
from http.client import HTTPConnection, HTTPException
import time


def ready(host, port):
    connection = HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request(
            "GET", "/api/session/csrf/",
            headers={"Host": host, "X-Forwarded-Proto": "https"},
        )
        response = connection.getresponse()
        return (
            response.status == 200
            and response.headers.get_content_type() == "application/json"
            and any(cookie.startswith("csrftoken=") for cookie in response.headers.get_all("Set-Cookie", []))
        )
    except (HTTPException, OSError):
        return False
    finally:
        connection.close()


def main():
    host = os.environ["SJERP_HTTP_HOST"]
    port = int(os.environ["SJERP_HTTP_PORT"])
    for attempt in range(8):
        if ready(host, port):
            print("ERP session HTTP probe passed.")
            return 0
        if attempt < 7:
            time.sleep(1)
    print("ERP session HTTP probe failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
