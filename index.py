import os
import json
import base64
import logging
import time
from aiohttp import web, ClientSession
from urllib.parse import urlencode
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# --- Configuration ---
# Google Credentials
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Microsoft Credentials
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")

# Common
REDIRECT_URI = os.getenv("REDIRECT_URI")

# --- Scopes ---
# Google Scopes (Admin removed)
SCOPES = {
    "drive": ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive.metadata.readonly"],
    "gmail": ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"],
    "calendar": ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/calendar.events"],
    "docs": ["https://www.googleapis.com/auth/documents"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "slides": ["https://www.googleapis.com/auth/presentations"],
    "forms": ["https://www.googleapis.com/auth/forms.body", "https://www.googleapis.com/auth/forms.responses.readonly"],
    "chat": ["https://www.googleapis.com/auth/chat.messages", "https://www.googleapis.com/auth/chat.spaces.readonly"],
    "contacts": ["https://www.googleapis.com/auth/contacts", "https://www.googleapis.com/auth/contacts.readonly"],
    "tasks": ["https://www.googleapis.com/auth/tasks"]
}
SCOPES["all"] = [s for scopes in SCOPES.values() for s in scopes]

# Microsoft Scopes
MS_SCOPES = {
    "mail": ["Mail.Read", "Mail.Send"],
    "onedrive": ["Files.Read", "Files.ReadWrite.All"],
    "calendar": ["Calendars.Read", "Calendars.ReadWrite"],
    "contacts": ["Contacts.Read"],
}

# Base scopes required to fetch the user's email address
BASE_SCOPES = ["https://www.googleapis.com/auth/userinfo.email", "openid"]
MS_BASE_SCOPES = ["User.Read", "offline_access"]

# --- UI Assets & Styles ---
SHARED_STYLES = """
<style>
    :root {
        --bg: #0a0b10;
        --card-bg: #13151f;
        --border: #232635;
        --accent: #3d5afe;
        --accent-hover: #536dfe;
        --text-main: #ffffff;
        --text-dim: #a3a3a3;
        --success: #10b981;
        --warning: #f59e0b;
        --error: #ef4444;
        --code-bg: #000000;
        --google-color: #ea4335;
        --ms-color: #00a4ef;
    }
    * { box-sizing: border-box; transition: all 0.2s ease; }
    body { 
        font-family: 'Inter', -apple-system, system-ui, sans-serif; 
        background: var(--bg); 
        color: var(--text-main); 
        line-height: 1.6; 
        margin: 0; 
        padding-bottom: 80px;
    }
    .container { max-width: 1000px; margin: 0 auto; padding: 0 24px; }
    
    .nav { display: flex; align-items: center; justify-content: space-between; padding: 24px 0; border-bottom: 1px solid var(--border); margin-bottom: 40px; }
    .logo { display: flex; align-items: center; gap: 12px; font-weight: 800; font-size: 20px; color: #ffffff; text-decoration: none; }
    .logo-box { background: var(--accent); color: #ffffff; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .nav-links { display: flex; gap: 24px; }
    .nav-links a { color: var(--text-dim); text-decoration: none; font-size: 14px; font-weight: 500; }
    .nav-links a:hover { color: #ffffff; }

    .hero { margin-bottom: 48px; text-align: center; }
    .hero h1 { font-size: 48px; font-weight: 900; margin: 0 0 16px; letter-spacing: -1.5px; background: linear-gradient(to right, #ffffff, #a3a3a3); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p { font-size: 18px; color: var(--text-dim); max-width: 600px; margin: 0 auto; }
    .status-pill { display: inline-flex; align-items: center; gap: 6px; background: rgba(16, 185, 129, 0.1); color: var(--success); padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: 600; margin-bottom: 24px; }

    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 32px; margin-bottom: 24px; box-shadow: 0 4px 24px rgba(0,0,0,0.2); }
    
    /* Centered Headings */
    .card-header { display: flex; align-items: center; justify-content: center; margin-bottom: 24px; }
    .card-title { font-size: 18px; font-weight: 800; color: #ffffff; margin: 0 0 24px 0; text-transform: uppercase; letter-spacing: 1px; text-align: center; width: 100%; border-bottom: 1px solid var(--border); padding-bottom: 16px; }

    /* API Endpoints */
    .ep-row { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border); }
    .ep-row:last-child { border-bottom: none; }
    .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; font-family: monospace; }
    .badge-get { background: rgba(61, 90, 254, 0.1); color: #ffffff; border: 1px solid var(--accent); }
    .badge-post { background: rgba(245, 158, 11, 0.1); color: var(--warning); border: 1px solid var(--warning); }
    .ep-path { font-family: monospace; font-size: 13px; color: var(--success); flex: 1; word-break: break-all; }
    .ep-desc { font-size: 13px; color: var(--text-dim); }

    /* Services Grid */
    .service-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
    .category-title { grid-column: 1 / -1; margin: 24px 0 8px 0; font-size: 14px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; display: flex; align-items: center; justify-content: center; gap: 8px; }
    .category-title:first-child { margin-top: 0; }
    .dot-google { width: 8px; height: 8px; border-radius: 50%; background: var(--google-color); }
    .dot-ms { width: 8px; height: 8px; border-radius: 50%; background: var(--ms-color); }
    
    .service-item { background: #1a1d29; border: 1px solid var(--border); padding: 16px; border-radius: 12px; display: flex; flex-direction: column; gap: 4px; cursor: default; }
    .service-item:hover { border-color: var(--accent); background: #232738; transform: translateY(-2px); }
    .service-name { font-weight: 600; font-size: 14px; color: #ffffff; }
    .service-path { font-family: monospace; font-size: 11px; color: var(--success); }

    /* Guide Steps */
    .guide-step { display: flex; gap: 16px; margin-bottom: 24px; position: relative; }
    .guide-step:not(:last-child)::before { content: ''; position: absolute; left: 15px; top: 32px; bottom: -24px; width: 2px; background: var(--border); }
    .step-number { width: 32px; height: 32px; border-radius: 50%; background: var(--card-bg); border: 2px solid var(--accent); display: flex; align-items: center; justify-content: center; font-weight: 700; color: #ffffff; font-size: 14px; flex-shrink: 0; z-index: 1; }
    .step-content { flex: 1; background: #1a1d29; border: 1px solid var(--border); padding: 20px; border-radius: 12px; transition: all 0.2s ease; width: 100%; overflow: hidden; }
    .step-content:hover { border-color: #31354b; background: #1e2230; }
    .step-content h3 { margin: 0 0 8px 0; font-size: 16px; color: #ffffff; }
    .step-content p { margin: 0 0 12px 0; font-size: 14px; color: var(--text-dim); line-height: 1.6; }
    code { background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; font-family: monospace; color: var(--warning); border: 1px solid var(--border); font-size: 12px; word-break: break-all; }

    /* Forms */
    .form-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px; }
    .form-group { margin-bottom: 20px; }
    .label { display: block; font-size: 12px; font-weight: 600; color: var(--text-dim); margin-bottom: 8px; text-transform: uppercase; }
    input, select { width: 100%; background: #000; border: 1px solid var(--border); color: #ffffff; padding: 12px 16px; border-radius: 8px; font-size: 14px; }
    input:focus, select:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(61, 90, 254, 0.2); }
    .btn { background: var(--accent); color: #ffffff; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 14px; width: 100%; display: inline-flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; }
    .btn:hover { background: var(--accent-hover); transform: translateY(-1px); }
    
    .code-container { position: relative; margin-top: 12px; width: 100%; }
    
    /* Code Blocks - Responsive wrapping */
    pre { 
        background: var(--code-bg); 
        padding: 40px 16px 16px 16px; 
        border-radius: 8px; 
        overflow-x: auto; 
        border: 1px solid var(--border); 
        font-size: 13px; 
        color: #ffffff; 
        margin: 0; 
        line-height: 1.5;
        white-space: pre-wrap; 
        word-break: break-all; 
    }
    .copy-btn { position: absolute; top: 8px; right: 8px; background: rgba(255,255,255,0.1); border: 1px solid var(--border); color: #ffffff; padding: 4px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; transition: 0.2s; z-index: 10; }
    .copy-btn:hover { background: var(--accent); color: #ffffff; }

    /* Legal Pages */
    .legal-content h1 { font-size: 32px; font-weight: 800; margin-bottom: 8px; color: #ffffff; letter-spacing: -0.5px; text-align: center; }
    .legal-content h2 { font-size: 18px; font-weight: 600; color: #ffffff; margin: 32px 0 12px; }
    .legal-content p, .legal-content li { font-size: 15px; color: var(--text-dim); line-height: 1.7; }
    .legal-content ul { padding-left: 24px; margin-bottom: 24px; }
    .updated { font-size: 13px; color: #a3a3a3; margin-bottom: 40px; font-weight: 500; text-align: center; }
    .legal-content a { color: #ffffff; text-decoration: underline; font-weight: 500; }
    .legal-content a:hover { text-decoration: none; color: #cccccc; }
    .highlight-box { background: rgba(61, 90, 254, 0.08); border-left: 4px solid var(--accent); padding: 16px 20px; border-radius: 0 8px 8px 0; margin: 24px 0; color: #ffffff; font-weight: 500; font-size: 15px; }

    .footer { text-align: center; margin-top: 60px; color: var(--text-dim); font-size: 13px; }
    .footer a { color: var(--text-main); text-decoration: none; font-weight: 600; }

    /* --- RESPONSIVE MOBILE ADJUSTMENTS --- */
    @media (max-width: 768px) {
        .container { padding: 0 16px; }
        .hero h1 { font-size: 32px; }
        .hero p { font-size: 15px; }
        .nav { flex-direction: column; gap: 16px; align-items: flex-start; }
        .nav-links { width: 100%; justify-content: flex-start; gap: 16px; }
        
        .card { padding: 20px; }
        .form-row { grid-template-columns: 1fr; gap: 0px; } 
        
        .ep-row { flex-direction: column; align-items: flex-start; gap: 8px; }
        .badge { margin-bottom: 4px; }
        
        .guide-step { flex-direction: column; gap: 12px; }
        .guide-step:not(:last-child)::before { display: none; } 
        .step-content { padding: 16px; }
        
        pre { padding: 36px 12px 12px 12px; font-size: 12px; }
    }
</style>
"""

# --- Middleware ---
@web.middleware
async def global_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        })
    try:
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except web.HTTPException as ex:
        raise ex
    except Exception as e:
        logger.error(f"Internal Error: {str(e)}", exc_info=True)
        return web.Response(text=f"Server Error: {str(e)}", status=500)

# --- Helpers ---
def decode_state(state_str: str) -> dict:
    try:
        padding = "=" * (4 - len(state_str) % 4)
        decoded = base64.urlsafe_b64decode(state_str + padding).decode()
        return json.loads(decoded)
    except:
        return {}

async def get_user_email(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    async with ClientSession() as session:
        # Standard Google UserInfo API - Works globally regardless of requested service
        async with session.get("https://www.googleapis.com/oauth2/v3/userinfo", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("email", "Unknown Google User")
    return "Unknown Google User"

async def get_ms_user_email(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    async with ClientSession() as session:
        # Standard Microsoft Graph endpoint for user profile
        async with session.get("https://graph.microsoft.com/v1.0/me", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("userPrincipalName") or data.get("mail", "Unknown MS User")
    return "Unknown Microsoft User"

# --- Handlers ---
async def home_handler(request):
    is_ready = all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI])
    status_msg = "System Operational" if is_ready else "Configuration Incomplete"
    
    warning_card = ""
    if not is_ready:
        warning_card = f"""
        <div class="card" style="border-color:var(--error); background: rgba(239, 68, 68, 0.05);">
            <h3 style="color:var(--error); margin-top:0; text-align:center;">⚠️ Missing Environment Variables</h3>
            <p style="color:var(--text-dim); font-size:14px; text-align:center;">Ensure GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, MS_CLIENT_ID, MS_CLIENT_SECRET, and REDIRECT_URI are set in your .env file.</p>
        </div>
        """

    services_html = ""
    
    # Category 1: Google Workspace
    services_html += '<div class="category-title"><div class="dot-google"></div> Google Workspace APIs</div>'
    for k in SCOPES.keys():
        name = "All Services" if k == "all" else k.capitalize()
        services_html += f'<div class="service-item"><span class="service-path">/start-auth/{k}</span><span class="service-name">{name}</span></div>'
    
    # Category 2: Microsoft Graph
    services_html += '<div class="category-title" style="margin-top:24px;"><div class="dot-ms"></div> Microsoft Graph APIs</div>'
    for k in MS_SCOPES.keys():
        name = k.capitalize()
        services_html += f'<div class="service-item"><span class="service-path">/start-auth/{k}</span><span class="service-name">{name}</span></div>'
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Open Auth Bridge — Centralized OAuth</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        {SHARED_STYLES}
    </head>
    <body>
        <div class="container">
            <nav class="nav">
                <a href="/" class="logo">
                    <div class="logo-box">UA</div>
                    Open Auth Bridge
                </a>
                <div class="nav-links">
                    <a href="/terms">Terms</a>
                    <a href="/privacy">Privacy</a>
                </div>
            </nav>

            <header class="hero">
                <div class="status-pill">
                    <span style="background:currentColor; width:8px; height:8px; border-radius:50%;"></span>
                    {status_msg}
                </div>
                <h1>Your Centralized OAuth Bridge.</h1>
                <p>A single endpoint to manage authentication for Google Workspace and Microsoft Graph APIs. Generate tokens manually or route them directly to your app via webhooks.</p>
            </header>

            {warning_card}

            <!-- 1. Token Generator Tool -->
            <div class="card">
                <h2 class="card-title">Token Generator Tool</h2>
                
                <div class="form-row">
                    <div class="form-group" style="margin-bottom: 0;">
                        <label class="label">Provider</label>
                        <select id="provider" onchange="updateServices()">
                            <option value="google">Google</option>
                            <option value="microsoft">Microsoft</option>
                        </select>
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                        <label class="label">Project/User ID</label>
                        <input type="text" id="uid" value="dev_tester" placeholder="e.g. user_123">
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                        <label class="label">Service Scope</label>
                        <select id="service"></select>
                    </div>
                </div>

                <button class="btn" onclick="startAuth()" style="margin-top: 10px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg>
                    &nbsp; Initiate Authorization
                </button>
            </div>

            <!-- 2. API Endpoints -->
            <div class="card">
                <h2 class="card-title">API Endpoints</h2>
                <div class="ep-row">
                    <span class="badge badge-get">GET</span>
                    <span class="ep-path">/start-auth/{{service}}</span>
                    <span class="ep-desc">Redirect user to provider consent screen</span>
                </div>
                <div class="ep-row">
                    <span class="badge badge-get">GET</span>
                    <span class="ep-path">/oauth_callback</span>
                    <span class="ep-desc">Provider callback — exchanges code for tokens</span>
                </div>
                <div class="ep-row">
                    <span class="badge badge-post">POST</span>
                    <span class="ep-path">/refresh</span>
                    <span class="ep-desc">Renew expired token (requires provider info in body)</span>
                </div>
            </div>

            <!-- 3. Available Services -->
            <div class="card">
                <h2 class="card-title">Available Services</h2>
                <div class="service-grid">
                    {services_html}
                </div>
            </div>

            <!-- 4. Detailed Integration Guide -->
            <div class="card">
                <h2 class="card-title">Integration Guide</h2>
                <p style="color:var(--text-dim); margin-bottom:28px; font-size:14px; text-align:center;">Follow these exact steps to connect your backend application with Open Auth Bridge via webhooks.</p>
                
                <div class="guide-step">
                    <div class="step-number">1</div>
                    <div class="step-content">
                        <h3>Construct the Routing Payload</h3>
                        <p>Create a JSON object containing three required keys:</p>
                        <ul style="margin-top:0; color:var(--text-dim); font-size:14px;">
                            <li><code>u</code>: Your internal User ID (e.g., "user_890")</li>
                            <li><code>r</code>: Your server's Webhook URL where tokens will be delivered</li>
                            <li><code>p</code>: The provider name (<code>google</code> or <code>microsoft</code>)</li>
                        </ul>
                        <div class="code-container">
                            <pre id="step1">{{
  "u": "user_890",
  "r": "https://api.yourdomain.com/v1/save-tokens",
  "p": "microsoft"
}}</pre>
                        </div>
                    </div>
                </div>

                <div class="guide-step">
                    <div class="step-number">2</div>
                    <div class="step-content">
                        <h3>Redirect User to Auth Bridge</h3>
                        <p>Convert the JSON object to a string, Base64 encode it, and pass it via the <code>state</code> parameter. Redirect your user to this URL:</p>
                        <div class="code-container">
                            <pre id="step2">GET {request.scheme}://{request.host}/start-auth/onedrive?state=eyJ1IjoidXNlcl84OTAiLCJyIjoiaHR0cHM6Ly9hcGkueW91cmRvbWFpbi5jb20vdjEvc2F2ZS10b2tlbnMiLCJwIjoibWljcm9zb2Z0In0</pre>
                        </div>
                    </div>
                </div>

                <div class="guide-step">
                    <div class="step-number">3</div>
                    <div class="step-content">
                        <h3>Receive Tokens via Webhook</h3>
                        <p>Once the user grants permission, Auth Bridge will automatically send a <code>POST</code> request to your webhook URL with the following payload:</p>
                        <div class="code-container">
                            <pre id="step3">POST https://api.yourdomain.com/v1/save-tokens
Content-Type: application/json

{{
  "status": "success",
  "provider": "microsoft",
  "user_id": "user_890",
  "email": "user@outlook.com",
  "credentials": {{
    "access_token": "eyJ0eXAiOiJKV1...",
    "refresh_token": "M.R3_BAY...",
    "expires_at": 1704100000.5
  }}
}}</pre>
                        </div>
                        <p style="margin-top:12px; font-size:13px; color:var(--success);">Note: Your endpoint must return a <code>200 OK</code> status immediately upon receiving this request.</p>
                    </div>
                </div>

                <div class="guide-step" style="margin-bottom:0;">
                    <div class="step-number">4</div>
                    <div class="step-content">
                        <h3>Refresh Expired Tokens</h3>
                        <p>When the access token expires, send a direct POST request from your application backend to this endpoint to receive a new token:</p>
                        <div class="code-container">
                            <pre id="step4">POST {request.scheme}://{request.host}/refresh
Content-Type: application/json

{{
  "refresh_token": "M.R3_BAY...",
  "provider": "microsoft"
}}</pre>
                        </div>
                    </div>
                </div>
            </div>

            <div class="footer">
                Open Auth Bridge &copy; 2026 &middot; <a href="https://arshman.me">arshman.me</a>
            </div>
        </div>

        <script>
            const scopes = {{
                google: {list(SCOPES.keys())},
                microsoft: {list(MS_SCOPES.keys())}
            }};

            function updateServices() {{
                const provider = document.getElementById('provider').value;
                const serviceSelect = document.getElementById('service');
                serviceSelect.innerHTML = '';
                
                scopes[provider].forEach(s => {{
                    const opt = document.createElement('option');
                    opt.value = s;
                    opt.innerText = s === 'all' ? 'All Services' : s.charAt(0).toUpperCase() + s.slice(1);
                    serviceSelect.appendChild(opt);
                }});
            }}

            function startAuth() {{
                const uid = document.getElementById('uid').value;
                const service = document.getElementById('service').value;
                const provider = document.getElementById('provider').value;
                const r = 'manual'; 
                
                const stateObj = {{ u: uid, r: r, p: provider }};
                const stateBase64 = btoa(JSON.stringify(stateObj)).replace(/=/g, "");
                window.location.href = `/start-auth/${{service}}?state=${{stateBase64}}`;
            }}

            window.onload = updateServices;
        </script>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def start_auth_handler(request):
    state_raw = request.query.get("state")
    if not state_raw:
        return web.Response(text="Missing state parameter.", status=400)

    state_data = decode_state(state_raw)
    provider = state_data.get("p", "google")
    service = request.match_info.get("service")

    if provider == "google":
        if service not in SCOPES:
            return web.Response(text=f"Unknown Google service '{service}'", status=400)
        # Adding BASE_SCOPES so we always have permission to fetch the email
        scope_list = SCOPES[service] + BASE_SCOPES
        auth_url = "https://accounts.google.com/o/oauth2/auth"
        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(scope_list),
            "access_type": "offline",
            "prompt": "consent",
            "state": state_raw
        }
    elif provider == "microsoft":
        if service not in MS_SCOPES:
            return web.Response(text=f"Unknown Microsoft service '{service}'", status=400)
        # Adding MS_BASE_SCOPES so we always have permission to fetch the email
        scope_list = MS_SCOPES[service] + MS_BASE_SCOPES
        auth_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        params = {
            "client_id": MS_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(scope_list),
            "prompt": "consent",
            "state": state_raw
        }
    else:
        return web.Response(text="Invalid provider specified in state.", status=400)

    return web.HTTPFound(f"{auth_url}?{urlencode(params)}")

async def oauth_callback_handler(request):
    code = request.query.get("code")
    state_str = request.query.get("state")
    
    if not code or not state_str:
        return web.Response(text="Auth flow interrupted. Missing code or state.", status=400)

    state_data = decode_state(state_str)
    provider = state_data.get("p", "google")
    
    token_url = ""
    token_payload = {
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    if provider == "google":
        token_url = "https://oauth2.googleapis.com/token"
        token_payload["client_id"] = CLIENT_ID
        token_payload["client_secret"] = CLIENT_SECRET
    elif provider == "microsoft":
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        token_payload["client_id"] = MS_CLIENT_ID
        token_payload["client_secret"] = MS_CLIENT_SECRET
    else:
        return web.Response(text="Unknown provider in callback state.", status=400)

    try:
        async with ClientSession() as session:
            async with session.post(token_url, data=token_payload) as resp:
                token_data = await resp.json()
                if resp.status != 200:
                    err = token_data.get('error_description') or token_data.get('error')
                    return web.Response(text=f"OAuth Provider Error: {err}", status=400)

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
            
        return_url = state_data.get("r", "manual")
        user_id = state_data.get("u", "anonymous")

        # Fetch the email using the updated universal endpoints
        if provider == "google":
            email = await get_user_email(access_token)
        elif provider == "microsoft":
            email = await get_ms_user_email(access_token)
        else:
            email = "Unknown"
        
        payload = {
            "status": "success",
            "provider": provider,
            "user_id": user_id,
            "email": email,
            "credentials": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": time.time() + token_data.get("expires_in", 3600)
            }
        }

        if return_url == "manual":
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Success — Open Auth Bridge</title>
                {SHARED_STYLES}
            </head>
            <body style="display:flex; align-items:center; justify-content:center; min-height:100vh; padding:20px;">
                <div class="card" style="max-width:700px; width:100%;">
                    <div style="text-align:center; margin-bottom:32px;">
                        <div style="width:64px; height:64px; background:var(--success); color:white; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:32px; margin-bottom:16px;">✓</div>
                        <h1 style="font-size:28px; margin:0; color:#ffffff;">Access Granted</h1>
                        <p style="color:var(--text-dim);">Authorized for <strong style="color:#ffffff;">{email}</strong> ({provider.capitalize()})</p>
                    </div>
                    
                    <label class="label">Response Payload</label>
                    <div class="code-container">
                        <button class="copy-btn" onclick="copyCode('res')">Copy JSON</button>
                        <pre id="res">{json.dumps(payload, indent=2)}</pre>
                    </div>

                    <div style="margin-top:32px; display:flex; gap:12px; justify-content:center;">
                        <a href="/" class="btn" style="text-decoration:none; max-width:200px;">Back to Dashboard</a>
                    </div>
                </div>
                <script>
                    function copyCode(id) {{
                        const text = document.getElementById(id).innerText;
                        const el = document.createElement('textarea');
                        el.value = text;
                        document.body.appendChild(el);
                        el.select();
                        document.execCommand('copy');
                        document.body.removeChild(el);
                        const btn = event.target;
                        btn.innerText = 'Copied!';
                        setTimeout(() => btn.innerText = 'Copy JSON', 2000);
                    }}
                </script>
            </body>
            </html>
            """
            return web.Response(text=html, content_type="text/html")

        # Webhook Delivery
        async with ClientSession() as session:
            async with session.post(return_url, json=payload, timeout=15) as bot_resp:
                if bot_resp.status == 200:
                    return web.Response(text="<html><body style='background:#0a0b10; color:#ffffff; font-family:sans-serif; text-align:center; padding-top:100px;'><h1>Tokens Delivered</h1><p>Webhook returned 200 OK. You can close this window.</p></body></html>", content_type="text/html")
                return web.Response(text=f"Webhook Failed: {bot_resp.status}", status=500)

    except Exception as e:
        logger.error(f"Callback Error: {str(e)}")
        return web.Response(text=f"Callback Error: {str(e)}", status=500)

async def refresh_handler(request):
    try:
        data = await request.json()
        rt = data.get("refresh_token")
        provider = data.get("provider", "google")
        
        if not rt: 
            return web.Response(text="Missing refresh_token", status=400)

        token_url = ""
        payload = {
            "refresh_token": rt,
            "grant_type": "refresh_token",
        }

        if provider == "google":
            token_url = "https://oauth2.googleapis.com/token"
            payload["client_id"] = CLIENT_ID
            payload["client_secret"] = CLIENT_SECRET
        elif provider == "microsoft":
            token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            payload["client_id"] = MS_CLIENT_ID
            payload["client_secret"] = MS_CLIENT_SECRET
        else:
            return web.Response(text="Invalid provider", status=400)

        async with ClientSession() as session:
            async with session.post(token_url, data=payload) as resp:
                res = await resp.json()
                return web.json_response(res)
    except Exception as e:
        return web.Response(text=str(e), status=500)

async def terms_handler(request):
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Terms of Service — Open Auth Bridge</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        {SHARED_STYLES}
    </head>
    <body>
        <div class="container">
            <nav class="nav">
                <a href="/" class="logo">
                    <div class="logo-box">UA</div>
                    Open Auth Bridge
                </a>
                <div class="nav-links">
                    <a href="/terms">Terms</a>
                    <a href="/privacy">Privacy</a>
                </div>
            </nav>
            
            <div class="card legal-content" style="padding: 40px 48px;">
                <h1>Terms of Service</h1>
                <p class="updated">Last updated: May 2026</p>

                <h2>1. Acceptance of Terms</h2>
                <p>By using Open Auth Bridge ("Service") hosted at this domain, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use the Service.</p>

                <h2>2. Description of Service</h2>
                <p>Open Auth Bridge provides a centralized OAuth 2.0 authentication bridge that allows integrating applications to obtain, securely transport, and refresh Google Workspace and Microsoft Graph API credentials on behalf of users who explicitly grant permission.</p>

                <h2>3. Use of Third-Party APIs</h2>
                <p>This Service interfaces with Google and Microsoft APIs to authenticate users. By proceeding through the consent screens of these providers, you authorize this Service to:</p>
                <ul>
                    <li>Request access to the specific Google or Microsoft services you select.</li>
                    <li>Receive and temporarily hold your access and refresh tokens.</li>
                    <li>Transmit these tokens securely via webhook to the application that initiated the request.</li>
                    <li>Refresh your access token upon request from the integrating application.</li>
                </ul>

                <h2>4. Data Handling & Integrity</h2>
                <p>Tokens are intended strictly for delivery to the requesting application. The Service operates statelessly for token delivery; it does not permanently store, sell, share, or misuse your account data or tokens.</p>

                <h2>5. User Responsibilities</h2>
                <p>You and the integrating application are solely responsible for keeping your generated tokens secure after delivery. You may revoke access at any time via your <a href="https://myaccount.google.com/permissions" target="_blank">Google Account</a> or <a href="https://account.microsoft.com/account/privacy" target="_blank">Microsoft Account</a> settings.</p>

                <h2>6. Limitation of Liability</h2>
                <p>The Service is provided on an "as is" and "as available" basis without warranties of any kind. We are not liable for any damages arising from unauthorized access to your tokens after delivery, misconfiguration of webhooks, or service interruptions from upstream providers.</p>

                <h2>7. Contact Information</h2>
                <p>For any questions or concerns regarding these terms, please contact the service administrator at arshman.me.</p>
            </div>
            
            <div class="footer">
                Open Auth Bridge &copy; 2026 &middot; <a href="https://arshman.me">arshman.me</a>
            </div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def privacy_handler(request):
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Privacy Policy — Open Auth Bridge</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
        {SHARED_STYLES}
    </head>
    <body>
        <div class="container">
            <nav class="nav">
                <a href="/" class="logo">
                    <div class="logo-box">UA</div>
                    Open Auth Bridge
                </a>
                <div class="nav-links">
                    <a href="/terms">Terms</a>
                    <a href="/privacy">Privacy</a>
                </div>
            </nav>
            
            <div class="card legal-content" style="padding: 40px 48px;">
                <h1>Privacy Policy</h1>
                <p class="updated">Last updated: May 2026</p>

                <div class="highlight-box">
                    <strong>Summary:</strong> We act only as a delivery bridge for your Google and Microsoft tokens. We do not store, sell, or analyze your personal data.
                </div>

                <h2>1. Information We Collect</h2>
                <p>When you authenticate through Open Auth Bridge, the system temporarily handles the following data in memory:</p>
                <ul>
                    <li><strong>OAuth Credentials:</strong> Access token, refresh token, and expiration timestamps provided by Google or Microsoft.</li>
                    <li><strong>Basic Profile Info:</strong> Your email address, used solely to confirm successful authentication on the success screen and payload.</li>
                    <li><strong>Routing Metadata:</strong> The `state` parameter provided by the initiating application to ensure tokens are routed to the correct destination webhook.</li>
                </ul>

                <h2>2. How We Use Your Information</h2>
                <p>Your data is used exclusively to complete the standard OAuth 2.0 flow. Specifically, to deliver tokens to the initiating application and to refresh expired tokens when requested. We do not use your data for tracking, analytics, advertising, or profiling.</p>

                <h2>3. Data Storage & Retention</h2>
                <p><strong>We do not maintain a database of your tokens.</strong> Tokens are held in-memory exclusively during the callback processing and webhook delivery phase. Once the HTTP response is sent to the integrating application, the tokens are immediately discarded from our server memory.</p>

                <h2>4. Data Sharing</h2>
                <p>We do not sell, trade, or share your information with any third parties. Your data is strictly transferred between the OAuth provider (Google/Microsoft) and the application that explicitly initiated the authorization request via the configured webhook.</p>

                <h2>5. Third-Party API Policies</h2>
                <p>Our use and transfer of information received from external APIs adheres to strict provider guidelines:</p>
                <ul>
                    <li><strong>Google:</strong> Open Auth Bridge adheres to the <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank">Google API Services User Data Policy</a>, including the Limited Use requirements.</li>
                    <li><strong>Microsoft:</strong> Interactions follow the guidelines established by the Microsoft Identity Platform.</li>
                </ul>

                <h2>6. Revoking Access</h2>
                <p>Because we do not store your tokens, you cannot delete your account with us (as you do not have one). You retain full control over your data and can revoke the application's access at any time directly through your provider:</p>
                <ul>
                    <li><a href="https://myaccount.google.com/permissions" target="_blank">Google Account Permissions</a></li>
                    <li><a href="https://account.microsoft.com/account/privacy" target="_blank">Microsoft Account Privacy</a></li>
                </ul>

                <h2>7. Contact</h2>
                <p>If you have any questions about this Privacy Policy, please contact the service administrator at arshman.me.</p>
            </div>
            
            <div class="footer">
                Open Auth Bridge &copy; 2026 &middot; <a href="https://arshman.me">arshman.me</a>
            </div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

app = web.Application(middlewares=[global_middleware])
app.router.add_get('/', home_handler)
app.router.add_get('/terms', terms_handler)
app.router.add_get('/privacy', privacy_handler)
app.router.add_get('/start-auth/{service}', start_auth_handler)
app.router.add_get('/oauth_callback', oauth_callback_handler)
app.router.add_post('/refresh', refresh_handler)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    logger.info(f"🚀 Open Auth Bridge UI Ready on port {port}")
    web.run_app(app, host='0.0.0.0', port=port)
