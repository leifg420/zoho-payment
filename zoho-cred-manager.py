#!python3
import os
from pathlib import Path
import json
from base64 import b64encode, b64decode
from getpass import getpass
import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zoho_payments.log'),
        logging.StreamHandler()
    ]
)
class CredentialManager:
    def __init__(self, app_name: str = "zoho-invoice-manager"):
        self.app_name = app_name
        self.config_dir = Path.home() / ".config" / app_name
        self.config_file = self.config_dir / "config.enc"
        self.salt_file = self.config_dir / "salt"
        self.keyring_service = app_name
        self.keyring_username = "config_key"

    def _create_config_dir(self):
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def _generate_key(self, password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """Generate encryption key from password."""
        if salt is None:
            salt = os.urandom(16)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = b64encode(kdf.derive(password.encode()))
        return key, salt

    def _get_encryption_key(self) -> bytes:
        """Retrieve encryption key from keyring."""
        key = keyring.get_password(self.keyring_service, self.keyring_username)
        if not key:
            raise ValueError("Encryption key not found. Please initialize credentials first.")
        return key.encode()

    def initialize_credentials(self, password: str = None) -> None:
        """Initialize credential storage with encryption key."""
        self._create_config_dir()
        
        # Get password if not provided
        if password is None:
            password = getpass("Enter password for encrypting credentials: ")
            confirm = getpass("Confirm password: ")
            if password != confirm:
                raise ValueError("Passwords do not match")

        # Generate and store salt
        key, salt = self._generate_key(password)
        with open(self.salt_file, 'wb') as f:
            f.write(salt)

        # Store encryption key in system keyring
        keyring.set_password(self.keyring_service, self.keyring_username, key.decode())

    def store_credentials(self, credentials: dict) -> None:
        """Store encrypted credentials."""
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            
            # Encrypt credentials
            encrypted_data = fernet.encrypt(json.dumps(credentials).encode())
            
            # Save to file
            with open(self.config_file, 'wb') as f:
                f.write(encrypted_data)
                
            logging.info("Credentials stored successfully")
            
        except Exception as e:
            logging.error(f"Failed to store credentials: {str(e)}")
            raise

    def load_credentials(self) -> dict:
        """Load and decrypt credentials."""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError("No credentials found. Please store credentials first.")
                
            key = self._get_encryption_key()
            fernet = Fernet(key)
            
            # Read and decrypt
            with open(self.config_file, 'rb') as f:
                encrypted_data = f.read()
                
            decrypted_data = fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data)
            
        except Exception as e:
            logging.error(f"Failed to load credentials: {str(e)}")
            raise

    def update_credentials(self, new_credentials: dict) -> None:
        """Update existing credentials."""
        try:
            current_creds = self.load_credentials()
            current_creds.update(new_credentials)
            self.store_credentials(current_creds)
            logging.info("Credentials updated successfully")
            
        except FileNotFoundError:
            # If no existing credentials, just store new ones
            self.store_credentials(new_credentials)
            
        except Exception as e:
            logging.error(f"Failed to update credentials: {str(e)}")
            raise

    def delete_credentials(self) -> None:
        """Delete all stored credentials and encryption keys."""
        try:
            # Remove config file
            if self.config_file.exists():
                self.config_file.unlink()
                
            # Remove salt file
            if self.salt_file.exists():
                self.salt_file.unlink()
                
            # Remove encryption key from keyring
            keyring.delete_password(self.keyring_service, self.keyring_username)
            
            logging.info("Credentials deleted successfully")
            
        except Exception as e:
            logging.error(f"Failed to delete credentials: {str(e)}")
            raise

def setup_credentials():
    """Interactive function to set up Zoho credentials."""
    cred_manager = CredentialManager()
    
    print("\nZoho Invoice Manager - Credential Setup")
    print("======================================")
    
    # Initialize encryption
    password = getpass("\nEnter a master password to encrypt your credentials: ")
    confirm = getpass("Confirm master password: ")
    
    if password != confirm:
        print("Passwords do not match!")
        return
        
    cred_manager.initialize_credentials(password)
    
    # Get Zoho credentials
    credentials = {
        "organization_id": input("\nEnter Zoho Organization ID: "),
        "client_id": input("Enter Zoho Client ID: "),
        "client_secret": input("Enter Zoho Client Secret: "),
        "refresh_token": input("Enter Zoho Refresh Token: ")
    }
    
    # Optional default customer ID
    default_customer = input("\nEnter default customer ID (optional, press Enter to skip): ")
    if default_customer:
        credentials["default_customer_id"] = default_customer
        
    # Store credentials
    cred_manager.store_credentials(credentials)
    print("\nCredentials stored successfully!")
    
    return credentials

def get_zoho_credentials() -> dict:
    """Get Zoho credentials from encrypted storage."""
    cred_manager = CredentialManager()
    
    try:
        return cred_manager.load_credentials()
    except FileNotFoundError:
        print("No stored credentials found. Running first-time setup...")
        return setup_credentials()
    except Exception as e:
        logging.error(f"Error loading credentials: {str(e)}")
        raise