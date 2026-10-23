# Taskify web service

Django front end: user picker, project list, drag-and-drop Kanban board, task dialog, notifications.
It holds no database; all data comes from the API service through `boards/api_client.py`.

## Run

```sh
export TASKIFY_API_URL=http://localhost:8001 TASKIFY_API_TOKEN=<same token as API> DJANGO_SECRET_KEY=<random>
python manage.py runserver 8000
```

Set `TASKIFY_ENV=production` for HTTPS redirect, secure cookies and HSTS (terminate TLS in front; see `deploy/`).

## Security notes

- The acting user comes only from the signed session; browser-sent `X-Acting-User` is ignored.
- CSP forbids inline scripts; the browser script renders server data with `textContent` only.
- CSRF protection is on for every state-changing request.

## Test

```sh
python -m pytest -q
```
