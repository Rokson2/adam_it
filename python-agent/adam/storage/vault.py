"""
Encrypted secrets vault for Adam.
Uses Fernet (AES-128-CBC) encryption with PBKDF2 key derivation.
"""

import os
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class VaultError(Exception):
    """Base exception for vault operations."""

    pass


class VaultLockedError(VaultError):
    """Raised when trying to access locked vault."""

    pass


class Vault:
    """
    Encrypted secrets vault using Fernet encryption.

    Secrets are stored encrypted at rest. The vault must be unlocked
    with a passphrase before any operations can be performed.
    """

    VAULT_FILE = "secrets.enc"
    SALT_FILE = "salt.bin"

    def __init__(self, vault_dir: Path = None):
        """
        Initialize vault.

        Args:
            vault_dir: Directory for vault files. Defaults to ~/.adam/vault/
        """
        self.vault_dir = vault_dir or Path.home() / ".adam" / "vault"
        self.vault_path = self.vault_dir / self.VAULT_FILE
        self.salt_path = self.vault_dir / self.SALT_FILE
        self._fernet: Optional[Fernet] = None
        self._unlocked = False
        self._cache: dict = {}

    @property
    def is_unlocked(self) -> bool:
        """Check if vault is unlocked."""
        return self._unlocked

    @property
    def vault_exists(self) -> bool:
        """Check if vault file exists."""
        return self.vault_path.exists()

    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        """
        Derive encryption key from passphrase using PBKDF2.

        Args:
            passphrase: User passphrase
            salt: Random salt for key derivation

        Returns:
            Base64-encoded key for Fernet
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommended minimum
        )
        key = kdf.derive(passphrase.encode())
        return base64.urlsafe_b64encode(key)

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create new one."""
        if self.salt_path.exists():
            return self.salt_path.read_bytes()

        # Generate new salt
        salt = os.urandom(16)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.salt_path.write_bytes(salt)

        # Set restrictive permissions
        os.chmod(self.salt_path, 0o600)

        return salt

    def unlock(self, passphrase: str) -> bool:
        """
        Unlock vault with passphrase.

        For a new vault, this sets the passphrase.
        For existing vault, this verifies the passphrase.

        Args:
            passphrase: Vault passphrase

        Returns:
            True if unlock successful, False otherwise
        """
        salt = self._get_or_create_salt()
        key = self._derive_key(passphrase, salt)
        self._fernet = Fernet(key)

        if self.vault_path.exists():
            try:
                encrypted = self.vault_path.read_bytes()
                decrypted = self._fernet.decrypt(encrypted)
                self._cache = json.loads(decrypted)
                self._unlocked = True
                return True
            except Exception:
                # Wrong passphrase or corrupted vault
                self._fernet = None
                return False
        else:
            # New vault - create empty
            self._cache = {}
            self._save()
            self._unlocked = True

            # Set restrictive permissions
            os.chmod(self.vault_path, 0o600)

            return True

    def lock(self) -> None:
        """Lock vault and clear memory cache."""
        self._cache = {}
        self._fernet = None
        self._unlocked = False

    def _check_unlocked(self) -> None:
        """Raise error if vault is locked."""
        if not self._unlocked:
            raise VaultLockedError("Vault is locked. Call 'adam vault unlock' first.")

    def _save(self) -> None:
        """Save encrypted cache to disk."""
        if not self._fernet:
            raise VaultLockedError("Cannot save - vault not initialized")

        self.vault_dir.mkdir(parents=True, exist_ok=True)
        data = json.dumps(self._cache).encode()
        encrypted = self._fernet.encrypt(data)
        self.vault_path.write_bytes(encrypted)

    def set(self, key: str, value: str) -> None:
        """
        Store a secret.

        Args:
            key: Secret key name
            value: Secret value
        """
        self._check_unlocked()
        self._cache[key] = value
        self._save()

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve a secret.

        Args:
            key: Secret key name

        Returns:
            Secret value or None if not found
        """
        self._check_unlocked()
        return self._cache.get(key)

    def delete(self, key: str) -> bool:
        """
        Delete a secret.

        Args:
            key: Secret key name

        Returns:
            True if deleted, False if not found
        """
        self._check_unlocked()
        if key in self._cache:
            del self._cache[key]
            self._save()
            return True
        return False

    def list_keys(self) -> List[str]:
        """
        List all stored keys (not values).

        Returns:
            List of key names
        """
        self._check_unlocked()
        return list(self._cache.keys())

    def export_encrypted(self) -> bytes:
        """
        Export vault in encrypted form for backup.

        Returns:
            Encrypted vault data
        """
        self._check_unlocked()
        return self.vault_path.read_bytes()

    def import_encrypted(self, data: bytes, passphrase: str) -> bool:
        """
        Import vault from encrypted backup.

        Args:
            data: Encrypted vault data
            passphrase: Passphrase for the backup

        Returns:
            True if import successful
        """
        # Temporarily save and try to unlock
        temp_path = self.vault_path.with_suffix(".tmp")
        temp_path.write_bytes(data)

        # Try to decrypt with provided passphrase
        salt = self._get_or_create_salt()
        key = self._derive_key(passphrase, salt)
        test_fernet = Fernet(key)

        try:
            decrypted = test_fernet.decrypt(data)
            # Verify it's valid JSON
            json.loads(decrypted)

            # Replace current vault
            self.vault_path.write_bytes(data)
            os.chmod(self.vault_path, 0o600)

            # Re-unlock with new data
            self.lock()
            return self.unlock(passphrase)
        except Exception:
            temp_path.unlink(missing_ok=True)
            return False


# Singleton instance
_vault_instance: Optional[Vault] = None


def get_vault() -> Vault:
    """Get the global vault instance."""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = Vault()
    return _vault_instance
