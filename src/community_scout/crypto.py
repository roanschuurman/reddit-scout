"""Encryption utilities for sensitive data like API keys."""


from cryptography.fernet import Fernet, InvalidToken

from community_scout.config import settings


class EncryptionError(Exception):
    """Error during encryption/decryption."""

    pass


def _get_fernet() -> Fernet:
    """Get a Fernet instance using the configured encryption key."""
    key = settings.encryption_key
    if not key:
        raise EncryptionError(
            "ENCRYPTION_KEY not configured. Generate one with: "
            "python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'"
        )

    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        raise EncryptionError(f"Invalid encryption key format: {e}") from e


def encrypt(plaintext: str) -> str:
    """
    Encrypt a string using Fernet symmetric encryption.

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded encrypted string

    Raises:
        EncryptionError: If encryption fails
    """
    if not plaintext:
        return ""

    try:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(plaintext.encode())
        return encrypted.decode()
    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {e}") from e


def decrypt(ciphertext: str) -> str:
    """
    Decrypt a Fernet-encrypted string.

    Args:
        ciphertext: The encrypted string (base64-encoded)

    Returns:
        Decrypted plaintext string

    Raises:
        EncryptionError: If decryption fails
    """
    if not ciphertext:
        return ""

    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken:
        raise EncryptionError("Invalid or corrupted encrypted data")
    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Decryption failed: {e}") from e


def generate_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        A new base64-encoded encryption key
    """
    return Fernet.generate_key().decode()
