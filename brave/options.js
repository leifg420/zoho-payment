document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('zohoConfigForm');
  const status = document.getElementById('status');

  // Load saved configuration
  chrome.storage.sync.get(['zohoConfig'], (result) => {
    const config = result.zohoConfig || {};
    
    document.getElementById('organizationId').value = config.organizationId || '';
    document.getElementById('clientId').value = config.clientId || '';
    document.getElementById('clientSecret').value = config.clientSecret || '';
    document.getElementById('refreshToken').value = config.refreshToken || '';
  });

  // Save configuration
  form.addEventListener('submit', (e) => {
    e.preventDefault();

    const zohoConfig = {
      organizationId: document.getElementById('organizationId').value,
      clientId: document.getElementById('clientId').value,
      clientSecret: document.getElementById('clientSecret').value,
      refreshToken: document.getElementById('refreshToken').value
    };

    // Validate configuration
    if (!zohoConfig.organizationId || !zohoConfig.clientId || 
        !zohoConfig.clientSecret || !zohoConfig.refreshToken) {
      status.textContent = 'Please fill in all fields.';
      status.style.color = 'red';
      return;
    }

    // Save to chrome storage
    chrome.storage.sync.set({ zohoConfig }, () => {
      status.textContent = 'Configuration saved successfully!';
      status.style.color = 'green';
    });
  });
});
