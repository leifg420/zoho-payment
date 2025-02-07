import requests
import json
from datetime import datetime, timedelta
import logging
import os
import argparse
from typing import List, Dict, Optional, Tuple
import csv
from pathlib import Path

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
        self.default_customer_id = os.getenv("ZOHO_DEFAULT_CUSTOMER_ID")
        
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

    def get_invoices(self, status: Optional[str] = None, date_start: Optional[str] = None, 
                     date_end: Optional[str] = None) -> List[Dict]:
        """Fetch invoices with optional filters."""
        url = f"{self.base_url}/invoices"
        params = {}
        
        if status:
            params["status"] = status
            params["filter_by"] = f"Status.{status.capitalize()}"
            
        if date_start:
            params["date_start"] = date_start
        if date_end:
            params["date_end"] = date_end
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch invoices: {response.text}")
        
        return response.json()["invoices"]

    def get_customers(self) -> List[Dict]:
        """Fetch all customers."""
        url = f"{self.base_url}/contacts?contact_type=customer"
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch customers: {response.text}")
            
        return response.json()["contacts"]

    def get_customer_by_name(self, name: str) -> Optional[Dict]:
        """Find a customer by name (case-insensitive partial match)."""
        customers = self.get_customers()
        name_lower = name.lower()
        
        matches = [c for c in customers if name_lower in c["contact_name"].lower()]
        return matches[0] if matches else None

    def create_quick_invoice(self, amount: float, description: str,
                           customer_id: Optional[str] = None,
                           line_items: Optional[List[Dict]] = None,
                           payment_terms: int = 0,
                           custom_fields: Optional[Dict] = None) -> Dict:
        """Create a quick invoice with optional custom line items and fields."""
        url = f"{self.base_url}/invoices"
        
        if not customer_id and not self.default_customer_id:
            raise ValueError("No customer ID provided and no default customer ID set")
        
        if not line_items:
            line_items = [{
                "name": description,
                "rate": amount,
                "quantity": 1
            }]
            
        invoice_data = {
            "customer_id": customer_id or self.default_customer_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "line_items": line_items,
            "payment_terms": payment_terms,
            "payment_terms_label": "Due on Receipt" if payment_terms == 0 else f"Net {payment_terms}"
        }
        
        if custom_fields:
            invoice_data["custom_fields"] = custom_fields
        
        response = requests.post(
            url,
            headers=self.get_headers(),
            data=json.dumps(invoice_data)
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to create invoice: {response.text}")
            
        return response.json()["invoice"]

    def apply_payment(self, invoice_id: str, amount: float, payment_date: str,
                     payment_mode: str = "cash", reference_number: Optional[str] = None,
                     notes: Optional[str] = None) -> Dict:
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
        
        if notes:
            payment_data["notes"] = notes
        
        response = requests.post(
            url, 
            headers=self.get_headers(), 
            data=json.dumps(payment_data)
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to apply payment to invoice {invoice_id}: {response.text}")
        
        return response.json()

    def void_invoice(self, invoice_id: str) -> Dict:
        """Void an existing invoice."""
        url = f"{self.base_url}/invoices/{invoice_id}/void"
        response = requests.post(url, headers=self.get_headers())
        
        if response.status_code != 200:
            raise Exception(f"Failed to void invoice {invoice_id}: {response.text}")
            
        return response.json()

    def generate_statement(self, customer_id: str, start_date: str, end_date: str) -> Dict:
        """Generate a customer statement for a date range."""
        url = f"{self.base_url}/contacts/{customer_id}/statements"
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to generate statement: {response.text}")
            
        return response.json()

def create_quick_paid_invoice(zoho: ZohoAPI, amount: float, description: str,
                            customer_id: Optional[str] = None,
                            payment_mode: str = "cash",
                            custom_fields: Optional[Dict] = None) -> Dict:
    """Create an invoice and immediately apply payment."""
    # Create the invoice
    invoice = zoho.create_quick_invoice(
        amount=amount,
        description=description,
        customer_id=customer_id,
        custom_fields=custom_fields
    )
    logging.info(f"Created invoice {invoice['invoice_id']} for amount {amount}")
    
    # Apply payment
    payment = zoho.apply_payment(
        invoice_id=invoice["invoice_id"],
        amount=amount,
        payment_date=datetime.now().strftime("%Y-%m-%d"),
        payment_mode=payment_mode
    )
    logging.info(f"Applied payment for invoice {invoice['invoice_id']}")
    
    return {"invoice": invoice, "payment": payment}

def process_open_invoices(zoho: ZohoAPI, payment_mode: str = "cash", 
                         max_age_days: Optional[int] = None):
    """Process all open invoices with optional age filter."""
    date_start = None
    if max_age_days:
        date_start = (datetime.now() - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
    
    logging.info("Fetching open invoices...")
    open_invoices = zoho.get_invoices(status="unpaid", date_start=date_start)
    logging.info(f"Found {len(open_invoices)} open invoices")
    
    results = []
    for invoice in open_invoices:
        try:
            payment_date = datetime.now().strftime("%Y-%m-%d")
            payment_result = zoho.apply_payment(
                invoice_id=invoice["invoice_id"],
                amount=float(invoice["balance"]),
                payment_date=payment_date,
                payment_mode=payment_mode
            )
            
            results.append({
                "invoice_id": invoice["invoice_id"],
                "amount": invoice["balance"],
                "status": "success"
            })
            
            logging.info(
                f"Successfully applied payment for invoice {invoice['invoice_id']}, "
                f"amount: {invoice['balance']}"
            )
            
        except Exception as e:
            results.append({
                "invoice_id": invoice["invoice_id"],
                "amount": invoice["balance"],
                "status": "failed",
                "error": str(e)
            })
            logging.error(
                f"Failed to process payment for invoice {invoice['invoice_id']}: {str(e)}"
            )
            continue
    
    return results

def export_results_to_csv(results: List[Dict], filename: str):
    """Export processing results to CSV file."""
    if not results:
        return
        
    fields = results[0].keys()
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

def process_bulk_invoices_from_csv(zoho: ZohoAPI, csv_file: str) -> List[Dict]:
    """Create and pay multiple invoices from CSV file."""
    results = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                result = create_quick_paid_invoice(
                    zoho,
                    amount=float(row['amount']),
                    description=row['description'],
                    customer_id=row.get('customer_id'),
                    payment_mode=row.get('payment_mode', 'cash'),
                    custom_fields=json.loads(row.get('custom_fields', '{}'))
                )
                results.append({
                    "row": row,
                    "status": "success",
                    "invoice_id": result["invoice"]["invoice_id"]
                })
            except Exception as e:
                results.append({
                    "row": row,
                    "status": "failed",
                    "error": str(e)
                })
    return results

def main():
    parser = argparse.ArgumentParser(description='Zoho Invoice Payment Manager')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Quick invoice command
    quick = subparsers.add_parser('quick', help='Create a quick invoice with immediate payment')
    quick.add_argument('--amount', type=float, required=True, help='Invoice amount')
    quick.add_argument('--description', type=str, required=True, help='Invoice description')
    quick.add_argument('--customer-id', type=str, help='Override default customer ID')
    quick.add_argument('--payment-mode', type=str, default='cash', help='Payment mode')
    quick.add_argument('--custom-fields', type=json.loads, help='Custom fields as JSON')
    
    # Process open invoices command
    process = subparsers.add_parser('process', help='Process open invoices')
    process.add_argument('--payment-mode', type=str, default='cash', help='Payment mode')
    process.add_argument('--max-age-days', type=int, help='Maximum age of invoices to process')
    process.add_argument('--export-csv', type=str, help='Export results to CSV file')
    
    # Bulk invoice processing from CSV
    bulk = subparsers.add_parser('bulk', help='Process bulk invoices from CSV')
    bulk.add_argument('--csv-file', type=str, required=True, help='Input CSV file')
    bulk.add_argument('--export-csv', type=str, help='Export results to CSV file')
    
    # Customer management
    customer = subparsers.add_parser('customer', help='Customer management')
    customer.add_argument('--search', type=str, help='Search customer by name')
    customer.add_argument('--statement', type=str, help='Generate statement for customer ID')
    customer.add_argument('--start-date', type=str, help='Statement start date (YYYY-MM-DD)')
    customer.add_argument('--end-date', type=str, help='Statement end date (YYYY-MM-DD)')
    
    args = parser.parse_args()

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
        
        if args.command == 'quick':
            result = create_quick_paid_invoice(
                zoho,
                amount=args.amount,
                description=args.description,
                customer_id=args.customer_id,
                payment_mode=args.payment_mode,
                custom_fields=args.custom_fields
            )
            logging.info(f"Quick invoice created and paid: {result['invoice']['invoice_number']}")
            
        elif args.command == 'process':
            results = process_open_invoices(
                zoho,
                