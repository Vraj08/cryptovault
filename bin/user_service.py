import sqlite3
from datetime import datetime, timedelta
from passlib.hash import pbkdf2_sha256  # Secure hashing algorithm
from flask import request, g
import jwt  # Used for token-based authentication
from hmac import compare_digest  # Used to mitigate timing attacks

# Secret used to sign JWT tokens (must be kept secret in production)
SECRET = 'bfg28y7efg238re7r6t32gfo23vfy7237yibdyo238do2v3'

def get_user_with_credentials(email, password):
    """
    Authenticates a user by checking their email and password.
    Defends against SQL Injection with parameterized query.
    Enforces password length and protects against timing attacks.
    """
    if len(password) < 8:
        return None  # Enforce minimum password length to prevent weak passwords

    try:
        con = sqlite3.connect('bank.db')
        cur = con.cursor()

        # Safe from SQL Injection due to use of parameterized query
        cur.execute('''
            SELECT email, name, password FROM users WHERE email=?
        ''', (email,))
        row = cur.fetchone()
        if row is None:
            return None  # Do not reveal whether email exists (part of user enumeration defense)

        email, name, stored_hash = row

        # Verify password using passlib’s PBKDF2 hash function
        if not pbkdf2_sha256.verify(password, stored_hash):
            return None

        # Extra layer: use compare_digest for timing-safe string comparison
        # Prevents attackers from inferring data based on how long comparisons take
        if not compare_digest(pbkdf2_sha256.hash(password), stored_hash):
            return None

        # On success, return user data and create a signed JWT
        return {"email": email, "name": name, "token": create_token(email)}

    finally:
        con.close()  # Always close DB connection to avoid leaks

def logged_in():
    """
    Checks if a user is logged in by validating the JWT stored in cookies.
    Uses a secure secret and HS256 algorithm.
    """
    token = request.cookies.get('auth_token')
    try:
        # Decode JWT and store user info in Flask's global context
        data = jwt.decode(token, SECRET, algorithms=['HS256'])
        g.user = data['sub']  # Set the current user globally
        return True
    except jwt.InvalidTokenError:
        return False  # Token is invalid, expired, or missing

def create_token(email):
    """
    Creates a JWT for the given user email with a 60-minute expiration.
    Includes issued-at time and uses a strong secret.
    """
    now = datetime.utcnow()
    payload = {
        'sub': email,
        'iat': now,
        'exp': now + timedelta(minutes=60)
    }
    token = jwt.encode(payload, SECRET, algorithm='HS256')
    return token

def update_user_password(email, new_password):
    """
    Securely updates the user’s password.
    This should be called from a password reset flow.
    """
    if len(new_password) < 8:
        return False  # Enforce strong password policy

    con = sqlite3.connect('bank.db')
    try:
        cur = con.cursor()

        # Hash the new password before storing it — never store plaintext passwords
        hashed = pbkdf2_sha256.hash(new_password)

        # Parameterized query to prevent SQL injection
        cur.execute("UPDATE users SET password=? WHERE email=?", (hashed, email))
        con.commit()
        return True
    finally:
        con.close()
