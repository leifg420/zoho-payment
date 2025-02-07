#!python3

# Add these to the main argument parser subparsers
import argparse
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
# Import or define CredentialManager
try:
    from credential_manager import CredentialManager  # type: ignore # Assuming it's defined in credential_manager.py
except ImportError:
    import sys
    sys.path.append('zoho-cred-manager.py')  # Replace with the actual path to credential_manager.py
    from credential_manager import CredentialManager # type: ignore

parser = argparse.ArgumentParser(description='Zoho Payment Configuration')
subparsers = parser.add_subparsers(dest='command', help='Sub-command help')

# Config management command
config = subparsers.add_parser('config', help='Credential management')
config_sub = config.add_subparsers(dest='config_command', help='Config command to execute')

# Setup new credentials
setup = config_sub.add_parser('setup', help='Setup new credentials')

# Update existing credentials
update = config_sub.add_parser('update', help='Update specific credentials')
update.add_argument('--organization-id', help='Update organization ID')
update.add_argument('--client-id', help='Update client ID')
update.add_argument('--client-secret', help='Update client secret')
update.add_argument('--refresh-token', help='Update refresh token')
update.add_argument('--default-customer-id', help='Update default customer ID')

# Delete credentials
delete = config_sub.add_parser('delete', help='Delete all stored credentials')

# Parse the arguments
args = parser.parse_args()

# Modify the main() function to handle config commands
if args.command == 'config':
    cred_manager = CredentialManager()
    
    if args.config_command == 'setup':
        cred_manager.setup_credentials()
        
    elif args.config_command == 'update':
        new_creds = {}
        if args.organization_id:
            new_creds['organization_id'] = args.organization_id
        if args.client_id:
            new_creds['client_id'] = args.client_id
        if args.client_secret:
            new_creds['client_secret'] = args.client_secret
        if args.refresh_token:
            new_creds['refresh_token'] = args.refresh_token
        if args.default_customer_id:
            new_creds['default_customer_id'] = args.default_customer_id
            
        if new_creds:
            cred_manager.update_credentials(new_creds)
            print("Credentials updated successfully!")
        
    elif args.config_command == 'delete':
        confirm = input("Are you sure you want to delete all stored credentials? (yes/no): ")
        if confirm.lower() == 'yes':
            cred_manager.delete_credentials()
            print("Credentials deleted successfully!")

# Replace the config loading in main() with:
try:
    config = cred_manager.get_zoho_credentials()
except Exception as e:
    logging.error(f"Failed to load credentials: {str(e)}")
    raise