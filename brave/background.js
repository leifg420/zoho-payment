chrome.runtime.onInstalled.addListener(() => {
  // Initialize extension settings
  chrome.storage.sync.set({
    zohoConfig: {
      organizationId: '',
      clientId: '',
      clientSecret: '',
      refreshToken: ''
    }
  });
});

// Handle API requests from popup or other parts of the extension
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'fetchAccessToken') {
    fetchAccessToken(request.config)
      .then(token => sendResponse({ token: token }))
      .catch(error => sendResponse({ error: error.message }));
    return true; // Indicates we wish to send a response asynchronously
  }
  
  if (request.action === 'callZohoAPI') {
    callZohoAPI(request.config, request.endpoint, request.method, request.data)
      .then(response => sendResponse({ success: true, data: response }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

async function fetchAccessToken(config) {
  const response = await fetch('https://accounts.zoho.com/oauth/v2/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams({
      refresh_token: config.refreshToken,
      client_id: config.clientId,
      client_secret: config.clientSecret,
      grant_type: 'refresh_token'
    })
  });

  if (!response.ok) {
    throw new Error('Failed to fetch access token');
  }

  const data = await response.json();
  return data.access_token;
}

async function callZohoAPI(config, endpoint, method = 'GET', data = null) {
  const accessToken = await fetchAccessToken(config);
  
  const headers = {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
    'organization_id': config.organizationId
  };

  const options = {
    method: method,
    headers: headers
  };

  if (data) {
    options.body = JSON.stringify(data);
  }

  const response = await fetch(`https://books.zoho.com/api/v3/${endpoint}`, options);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API call failed: ${errorText}`);
  }

  return await response.json();
}
