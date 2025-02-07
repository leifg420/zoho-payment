document.addEventListener('DOMContentLoaded', () => {
  // Retrieve stored configuration
  chrome.storage.sync.get(['zohoConfig'], (result) => {
    const config = result.zohoConfig || {};
    
    // Check if configuration is complete
    if (!config.organizationId || !config.clientId || !config.clientSecret || !config.refreshToken) {
      document.getElementById('resultArea').innerHTML = 
        '<p class="error">Please configure Zoho API settings in Options</p>';
      return;
    }

    // List Customers
    document.getElementById('listCustomersBtn').addEventListener('click', async () => {
      try {
        const response = await sendAPIRequest(config, 'contacts', 'GET');
        displayResults(response.contacts);
      } catch (error) {
        displayError(error);
      }
    });

    // Add Customer
    document.getElementById('addCustomerBtn').addEventListener('click', async () => {
      const name = document.getElementById('customerName').value;
      const email = document.getElementById('customerEmail').value;

      if (!name) {
        displayError('Customer name is required');
        return;
      }

      try {
        const customerData = {
          contact_name: name,
          email: email
        };

        const response = await sendAPIRequest(config, 'contacts', 'POST', customerData);
        displayResults(response.contact, 'Customer Added Successfully');
      } catch (error) {
        displayError(error);
      }
    });

    // Create Quick Invoice
    document.getElementById('createQuickInvoiceBtn').addEventListener('click', async () => {
      const description = document.getElementById('invoiceDescription').value;
      const amount = document.getElementById('invoiceAmount').value;

      if (!description || !amount) {
        displayError('Description and amount are required');
        return;
      }

      try {
        const invoiceData = {
          customer_name: 'Default Customer', // You might want to make this dynamic
          line_items: [{
            name: description,
            rate: parseFloat(amount),
            quantity: 1
          }],
          date: new Date().toISOString().split('T')[0]
        };

        const response = await sendAPIRequest(config, 'invoices', 'POST', invoiceData);
        displayResults(response.invoice, 'Invoice Created Successfully');
      } catch (error) {
        displayError(error);
      }
    });

    // Generate Report
    document.getElementById('generateReportBtn').addEventListener('click', async () => {
      try {
        const endDate = new Date().toISOString().split('T')[0];
        const startDate = new Date(new Date().setMonth(new Date().getMonth() - 1)).toISOString().split('T')[0];

        const response = await sendAPIRequest(config, `invoices?date_after=${startDate}&date_before=${endDate}`, 'GET');
        
        // Basic report generation
        const report = {
          totalInvoices: response.invoices.length,
          totalAmount: response.invoices.reduce((sum, inv) => sum + parseFloat(inv.total || 0), 0),
          startDate: startDate,
          endDate: endDate
        };

        displayResults(report, 'Monthly Invoice Report');
      } catch (error) {
        displayError(error);
      }
    });
  });
});

// Utility function to send API requests
async function sendAPIRequest(config, endpoint, method, data = null) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({
      action: 'callZohoAPI',
      config: config,
      endpoint: endpoint,
      method: method,
      data: data
    }, (response) => {
      if (response.success) {
        resolve(response.data);
      } else {
        reject(new Error(response.error));
      }
    });
  });
}

// Display results in the result area
function displayResults(data, title = 'Results') {
  const resultArea = document.getElementById('resultArea');
  resultArea.innerHTML = `
    <h3>${title}</h3>
    <pre>${JSON.stringify(data, null, 2)}</pre>
  `;
}

// Display errors
function displayError(error) {
  const resultArea = document.getElementById('resultArea');
  resultArea.innerHTML = `
    <p class="error">Error: ${error.message || error}</p>
  `;
}
