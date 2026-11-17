"""Create the named ERP administrator using a guest-encrypted password."""
import base64
import os
import socket
import subprocess


def main():
    if os.geteuid() != 0 or socket.gethostname().split(".")[0] != "sjerp-image-test":
        raise SystemExit("Unexpected acceptance host")
    encrypted = base64.b64decode(os.environ.pop("SJERP_ADMIN_PASSWORD_ENVELOPE"), validate=True)
    password = subprocess.run(
        ["openssl", "pkeyutl", "-decrypt", "-inkey", "/etc/sjerp/a/lan-https.key",
         "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha256",
         "-pkeyopt", "rsa_mgf1_md:sha256"],
        input=encrypted, capture_output=True, check=True,
    ).stdout.decode("ascii")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()

    from django.contrib.auth import get_user_model, password_validation
    from django.db import connection, transaction

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        if cursor.fetchone() != ("sjerp_a", "sjerp_a_runtime"):
            raise SystemExit("Unexpected database identity")
    users = get_user_model()
    with transaction.atomic():
        if users.objects.filter(username="johnson").exists():
            raise SystemExit("johnson already exists; no changes made")
        user = users(username="johnson", first_name="姚战森",
                     is_staff=True, is_superuser=True, is_active=True)
        password_validation.validate_password(password, user)
        user.set_password(password)
        user.full_clean()
        user.save(force_insert=True)
    print("johnson created and validated as an active ERP superuser")


if __name__ == "__main__":
    main()
