"""Explicit local operator creation; ordinary sign-up can never choose this role."""
import argparse
import getpass
import secrets
from .app import app, normalize_email, password_hash

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create-platform-admin"])
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Platform password (12+ characters): ")
    if len(password) < 12 or password != getpass.getpass("Confirm password: "):
        raise SystemExit("Password requirements or confirmation failed.")
    with app.state.db() as conn:
        conn.execute("INSERT INTO users VALUES(?,?,?,?,?,?)",
                     (secrets.token_hex(16), normalize_email(args.email), "Platform operator", password_hash(password), None, "platform_admin"))
    print("Local platform operator created. No customer membership granted.")

if __name__ == "__main__":
    main()
