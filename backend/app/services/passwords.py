import hashlib
import hmac
import secrets


HASH_NAME = "sha256"
ITERATIONS = 390_000
SALT_BYTES = 32
KEY_BYTES = 32


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    password_hash = hashlib.pbkdf2_hmac(
        HASH_NAME,
        password.encode("utf-8"),
        bytes.fromhex(salt),
        ITERATIONS,
        dklen=KEY_BYTES,
    ).hex()
    return f"pbkdf2_{HASH_NAME}${ITERATIONS}${salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected_hash = stored_hash.split("$", 3)
        hash_name = algorithm.removeprefix("pbkdf2_")
        iterations = int(iterations_text)
        actual_hash = hashlib.pbkdf2_hmac(
            hash_name,
            password.encode("utf-8"),
            bytes.fromhex(salt),
            iterations,
            dklen=len(bytes.fromhex(expected_hash)),
        ).hex()
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(actual_hash, expected_hash)

