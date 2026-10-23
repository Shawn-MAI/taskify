"""Production hardening of the Django settings (T050)."""

import subprocess
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
SNIPPET = (
    "import django;django.setup();from django.conf import settings as s;"
    "print(s.SECURE_SSL_REDIRECT, s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, s.SECURE_HSTS_SECONDS>0)"
)


def run(env):
    return subprocess.run(
        [sys.executable, "-c", SNIPPET],
        cwd=WEB,
        env={"PATH": "/usr/bin:/bin", "DJANGO_SETTINGS_MODULE": "taskify_web.settings", **env},
        capture_output=True,
        text=True,
    )


def test_production_enables_https_hardening():
    out = run({"TASKIFY_ENV": "production", "DJANGO_SECRET_KEY": "x" * 50})
    assert out.stdout.split() == ["True", "True", "True", "True"], out.stderr


def test_production_requires_secret_key():
    out = run({"TASKIFY_ENV": "production"})
    assert out.returncode != 0
