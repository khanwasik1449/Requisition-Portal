#!/usr/bin/env python3
"""
Reset the password of an existing Requisition Portal account.

Usage:
    python3 reset_password.py <username>               # prompts for password, not echoed
    python3 reset_password.py <username> --generate    # prints a random password
    python3 reset_password.py <username> <password>    # non-interactive (avoids shell history)

Loads .env so it talks to the real (PostgreSQL) database, sets the new password,
and revokes any active sessions for that user.
"""
import getpass
import os
import secrets
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Load .env before Django settings are imported.
env_path = os.path.join(HERE, '.env')
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

sys.path.insert(0, HERE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'requisition_portal.settings')

import django  # noqa: E402

django.setup()

from django.contrib.auth.password_validation import validate_password  # noqa: E402
from django.contrib.sessions.models import Session  # noqa: E402
from django.core.exceptions import ValidationError  # noqa: E402
from django.utils import timezone  # noqa: E402

from accounts.models import User  # noqa: E402

SPECIALS = '!@#$%^&*()-_=+'


def generate_password(length=20):
    """Random password containing all four character classes."""
    alphabet = string.ascii_letters + string.digits + SPECIALS
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in SPECIALS for c in pwd)):
            return pwd


def resolve_user(identifier):
    try:
        return User.objects.get(username=identifier)
    except User.DoesNotExist:
        pass
    matches = list(User.objects.filter(email__iexact=identifier))
    if len(matches) == 1:
        print(f"No username {identifier!r}; matched by email -> {matches[0].username}")
        return matches[0]
    if len(matches) > 1:
        sys.exit("Multiple users share that email: "
                 + ", ".join(u.username for u in matches))
    sys.exit(f"No such user: {identifier}")


def revoke_sessions(user):
    """Delete live sessions belonging to this user."""
    count = 0
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        try:
            data = session.get_decoded()
        except Exception:
            continue
        if data.get('_auth_user_id') == str(user.pk):
            session.delete()
            count += 1
    return count


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)

    user = resolve_user(args[0])

    if '--generate' in sys.argv:
        password, reveal = generate_password(), True
    elif len(args) > 1:
        password, reveal = args[1], False
    else:
        password = getpass.getpass(f"New password for {user.username}: ")
        if password != getpass.getpass("Confirm password: "):
            sys.exit("Passwords do not match.")
        reveal = False

    if not password:
        sys.exit("Empty password rejected.")

    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        sys.exit("Password rejected by validators:\n  - " + "\n  - ".join(exc.messages))

    was_active = user.is_active
    revoked = revoke_sessions(user)

    user.set_password(password)
    user.is_active = True
    if user.is_admin() and not user.is_staff:
        user.is_staff = True
    user.save()

    print()
    print(f"OK  username : {user.username}")
    print(f"    role     : {user.get_role_display()}")
    print(f"    superuser: {user.is_superuser}   staff: {user.is_staff}")
    if not was_active:
        print("    note     : account was inactive and has been re-activated.")
    print(f"    sessions : {revoked} revoked")
    if reveal:
        print(f"    password : {password}")
        print("              -> Copy this now; it is not recoverable after this.")
        print("              -> Change it in the app after your first login.")
    else:
        print("    password : (set, not shown)")


if __name__ == '__main__':
    main()
