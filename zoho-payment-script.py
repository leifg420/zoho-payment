#!python3
import requests
import json
import csv
from datetime import datetime, timedelta
import logging
import os
import argparse
import sys
from typing import List, Dict, Optional, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zoho_payments.log'),
        logging.StreamHandler()
    ]
)

class ZohoAPIEnhanced:
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

    def list_customers(self, search_term: Optional[str] = None, 
                       page: int = 1, 
                       per_page: int = 200) -> List[Dict]:
        """List customers with optional search and pagination."""
        url = f"{self.base_url}/contacts"
        params = {
            "page": page,
            "per_page": per_page
        }
        
        if search_term:
            params["search_text"] = search_term
        
        response = requests.get(
            url, 
            headers=self.get_headers(), 
            params=params
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch customers: {response.text}")
        
        return response.json()["contacts"]

    def create_customer(self, 
                        contact_name: str, 
                        email: Optional[str] = None, 
                        phone: Optional[str] = None,
                        billing_address: Optional[Dict] = None) -> Dict:
        """Create a new customer in Zoho Books."""
        url = f"{self.base_url}/contacts"
        
        customer_data = {
            "contact_name": contact_name,
            "email": email,
            "phone": phone,
            "billing_address": billing_address or {}
        }
        
        response = requests.post(
            url,
            headers=self.get_headers(),
            data=json.dumps(customer_data)
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to create customer: {response.text}")
        
        return response.json()["contact"]

    def get_invoices(self, 
                     status: Optional[str] = None, 
                     start_date: Optional[str] = None, 
                     end_date: Optional[str] = None,
                     customer_id: Optional[str] = None) -> List[Dict]:
        """Fetch invoices with advanced filtering."""
        url = f"{self.base_url}/invoices"
        params = {}
        
        if status:
            params["status"] = status
        
        if start_date:
            params["date_after"] = start_date
        
        if end_date:
            params["date_before"] = end_date
        
        if customer_id:
            params["customer_id"] = customer_id
        
        response = requests.get(
            url, 
            headers=self.get_headers(), 
            params=params
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch invoices: {response.text}")
        
        return response.json()["invoices"]

    def export_invoices(self, 
                        export_format: str = 'csv', 
                        filename: Optional[str] = None,
                        **filter_params) -> str:
        """Export invoices to CSV or JSON."""
        # Fetch invoices with applied filters
        invoices = self.get_invoices(**filter_params)
        
        # Generate default filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"zoho_invoices_{timestamp}"
        
        if export_format.lower() == 'csv':
            # Prepare CSV export
            output_filename = f"{filename}.csv"
            with open(output_filename, 'w', newline='') as csvfile:
                # Extract keys from first invoice to use as headers
                if invoices:
                    fieldnames = list(invoices[0].keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for invoice in invoices:
                        writer.writerow(invoice)
            
            return output_filename
        
        elif export_format.lower() == 'json':
            # Prepare JSON export
            output_filename = f"{filename}.json"
            with open(output_filename, 'w') as jsonfile:
                json.dump(invoices, jsonfile, indent=2)
            
            return output_filename
        
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

    def generate_payment_summary(self, 
                                 start_date: Optional[str] = None, 
                                 end_date: Optional[str] = None) -> Dict:
        """Generate a comprehensive payment summary."""
        # Fetch invoices (paid and unpaid)
        paid_invoices = self.get_invoices(status="paid", start_date=start_date, end_date=end_date)
        unpaid_invoices = self.get_invoices(status="unpaid", start_date=start_date, end_date=end_date)
        
        summary = {
            "total_invoices": len(paid_invoices) + len(unpaid_invoices),
            "paid_invoices": len(paid_invoices),
            "unpaid_invoices": len(unpaid_invoices),
            "total_invoice_amount": sum(float(inv.get('total', 0)) for inv in paid_invoices + unpaid_invoices),
            "total_paid_amount": sum(float(inv.get('total', 0)) for inv in paid_invoices),
            "total_unpaid_amount": sum(float(inv.get('total', 0)) for inv in unpaid_invoices),
            "date_range": {
                "start": start_date or "All time",
                "end": end_date or "All time"
            }
        }
        
        return summary

def main():
    parser = argparse.ArgumentParser(description='Advanced Zoho Invoice and Payment Management')
    
    # Customer Management
    customer_group = parser.add_argument_group('Customer Management')
    customer_group.add_argument('--list-customers', action='store_true', 
                                help='List all customers')
    customer_group.add_argument('--search-customer', type=str, 
                                help='Search customers by name or email')
    customer_group.add_argument('--add-customer', nargs='+', 
                                help='Add a new customer: name email phone')
    
    # Invoice Export
    export_group = parser.add_argument_group('Invoice Export')
    export_group.add_argument('--export-invoices', choices=['csv', 'json'], 
                              help='Export invoices to specified format')
    export_group.add_argument('--export-status', type=str, 
                              choices=['paid', 'unpaid', 'draft'], 
                              help='Filter invoices by status for export')
    export_group.add_argument('--export-start-date', type=str, 
                              help='Start date for invoice export (YYYY-MM-DD)')
    export_group.add_argument('--export-end-date', type=str, 
                              help='End date for invoice export (YYYY-MM-DD)')
    
    # Payment Summary
    summary_group = parser.add_argument_group('Payment Summary')
    summary_group.add_argument('--payment-summary', action='store_true', 
                               help='Generate payment summary report')
    summary_group.add_argument('--summary-start-date', type=str, 
                               help='Start date for payment summary (YYYY-MM-DD)')
    summary_group.add_argument('--summary-end-date', type=str, 
                               help='End date for payment summary (YYYY-MM-DD)')
    
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
        zoho = ZohoAPIEnhanced(**config)
        
        # Customer Management
        if args.list_customers:
            customers = zoho.list_customers()
            print(json.dumps(customers, indent=2))
        
        if args.search_customer:
            customers = zoho.list_customers(search_term=args.search_customer)
            print(json.dumps(customers, indent=2))
        
        if args.add_customer:
            if len(args.add_customer) < 1:
                raise ValueError("At least customer name is required")
            
            name = args.add_customer[0]
            email = args.add_customer[1] if len(args.add_customer) > 1 else None
            phone = args.add_customer[2] if len(args.add_customer) > 2 else None
            
            new_customer = zoho.create_customer(name, email, phone)
            print("New customer created:")
            print(json.dumps(new_customer, indent=2))
        
        # Invoice Export
        if args.export_invoices:
            export_params = {
                "export_format": args.export_invoices
            }
            
            if args.export_status:
                export_params["status"] = args.export_status
            
            if args.export_start_date:
                export_params["start_date"] = args.export_start_date
            
            if args.export_end_date:
                export_params["end_date"] = args.export_end_date
            
            exported_file = zoho.export_invoices(**export_params)
            print(f"Exported invoices to {exported_file}")
        
        # Payment Summary
        if args.payment_summary:
            summary_params = {}
            
            if args.summary_start_date:
                summary_params["start_date"] = args.summary_start_date
            
            if args.summary_end_date:
                summary_params["end_date"] = args.summary_end_date
            
            summary = zoho.generate_payment_summary(**summary_params)
            print("Payment Summary:")
            print(json.dumps(summary, indent=2))
        
    except Exception as e:
        logging.error(f"Script execution failed: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
