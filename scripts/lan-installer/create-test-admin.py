"""Interactively create a named ERP superuser on the isolated ALEX guest."""
import getpass
import os
import sys

import django


def main():
    if not os.isatty(sys.stdin.fileno()) or not os.isatty(sys.stdout.fileno()):
        raise SystemExit("This program requires the ALEX Hyper-V console.")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from django.utils.translation import activate
    activate("en")
    from django.contrib.auth import get_user_model, password_validation
    from django.core.exceptions import ValidationError
    from django.db import connection, transaction

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        if cursor.fetchone() != ("sjerp_a", "sjerp_a_runtime"):
            raise SystemExit("Unexpected database identity.")
    user_model = get_user_model()
    user = user_model(username="johnson", first_name="姚战森",
                      is_active=True, is_staff=True, is_superuser=True)
    print("ALEX ERP administrator setup: johnson")
    if user_model.objects.filter(username=user.username).exists():
        raise SystemExit("Account already exists; no changes made.")
    if input("Create this account on the acceptance instance? Type YES: ") != "YES":
        return
    while True:
        password = getpass.getpass("New password (hidden; blank cancels): ")
        if not password:
            return
        if not secrets_equal(password, getpass.getpass("Repeat new password: ")):
            print("Passwords did not match.")
            continue
        try:
            password_validation.validate_password(password, user)
        except ValidationError as error:
            print("\n".join(error.messages))
            continue
        break
    user.set_password(password)
    with transaction.atomic():
        user.full_clean()
        user.save(force_insert=True)
    print("Account created. Verify name and superuser role after HTTPS sign-in.")
    input("Press Enter to close setup.")


def secrets_equal(first, second):
    from secrets import compare_digest

    return compare_digest(first.encode(), second.encode())


if __name__ == "__main__":
    main()
