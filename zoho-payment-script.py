import requests
import json
from datetime import datetime
import logging
import os
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zoho_payments.log'),
        logging.StreamHandler()
    ]
)

class ZohoAPI:
    def __init__(self, organization_id: str, client_id: str, client_secret: str, refresh_token: str):
        self.base_url = "https://books.zoho.com/api/v3"
        self.organization_id = organization_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token = None
        
    def get_access_token(self) -> str:
        """Generate a new access token using the refresh token."""
        url = "https://accounts.zoho.com/oauth/v2/token"
        params = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(url, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.text}")
        
        self.access_token = response.json()["access_token"]
        return self.access_token

    def get_headers(self) -> Dict:
        """Get headers with authentication token."""
        if not self.access_token:
            self.get_access_token()
            
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "organization_id": self.organization_id
        }

    def get_open_invoices(self) -> List[Dict]:
        """Fetch all open invoices."""
        url = f"{self.base_url}/invoices"
        params = {
            "status": "unpaid",
            "filter_by": "Status.Unpaid"
        }
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch invoices: {response.text}")
        
        return response.json()["invoices"]

    def apply_payment(self, invoice_id: str, amount: float, payment_date: str, 
                     payment_mode: str = "cash", reference_number: Optional[str] = None) -> Dict:
        """Apply payment to a specific invoice."""
        url = f"{self.base_url}/customerpayments"
        
        payment_data = {
            "payment_mode": payment_mode,
            "amount": amount,
            "date": payment_date,
            "reference_number": reference_number or f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "invoices": [{
                "invoice_id": invoice_id,
                "amount_applied": amount
            }]
        }
        
        response = requests.post(
            url, 
            headers=self.get_headers(), 
            data=json.dumps(payment_data)
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to apply payment to invoice {invoice_id}: {response.text}")
        
        return response.json()

def main():
    # Load configuration from environment variables
    config = {
        "organization_id": os.getenv("ZOHO_ORGANIZATION_ID"),
        "client_id": os.getenv("ZOHO_CLIENT_ID"),
        "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
        "refresh_token": os.getenv("ZOHO_REFRESH_TOKEN")
    }
    
    # Validate configuration
    missing_configs = [k for k, v in config.items() if not v]
    if missing_configs:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_configs)}")
    
    try:
        # Initialize Zoho API client
        zoho = ZohoAPI(**config)
        
        # Get open invoices
        logging.info("Fetching open invoices...")
        open_invoices = zoho.get_open_invoices()
        logging.info(f"Found {len(open_invoices)} open invoices")
        
        # Process each invoice
        for invoice in open_invoices:
            try:
                payment_date = datetime.now().strftime("%Y-%m-%d")
                payment_result = zoho.apply_payment(
                    invoice_id=invoice["invoice_id"],
                    amount=float(invoice["balance"]),
                    payment_date=payment_date
                )
                
                logging.info(
                    f"Successfully applied payment for invoice {invoice['invoice_id']}, "
                    f"amount: {invoice['balance']}"
                )
                
            except Exception as e:
                logging.error(
                    f"Failed to process payment for invoice {invoice['invoice_id']}: {str(e)}"
                )
                continue
                
    except Exception as e:
        logging.error(f"Script execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
