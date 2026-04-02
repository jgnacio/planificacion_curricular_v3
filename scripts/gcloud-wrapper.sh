#!/bin/sh
exec /app/.venv/bin/python3 -c "
import sys, os
args = sys.argv[1:]
if 'print-access-token' in args:
    import google.auth, google.auth.transport.requests
    creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    creds.refresh(google.auth.transport.requests.Request())
    print(creds.token)
elif 'get-value' in args and 'project' in args:
    print(os.environ.get('GOOGLE_CLOUD_PROJECT', ''))
else:
    print('unhandled', args, file=sys.stderr); sys.exit(1)
" "$@"
