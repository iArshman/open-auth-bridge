# Open Auth Bridge

A stateless OAuth 2.0 bridge for Google Workspace and Microsoft Graph APIs. It handles the full authorization code flow, fetches the authenticated user's email, and delivers tokens — either via webhook to an integrating application or directly to the user's browser for manual use.

---

## How It Works

1. An integrating application constructs a `state` parameter (base64-encoded JSON) and redirects the user to `/start-auth/{service}`.
2. The bridge redirects the user to the appropriate Google or Microsoft consent screen.
3. After the user grants access, the provider redirects back to `/oauth_callback`.
4. The bridge exchanges the authorization code for tokens, fetches the user's email, and either:
   - **Posts the payload as JSON to the webhook URL** specified in the `state`, or
   - **Displays the token payload on screen** if `return_url` is `"manual"`.

---

## Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Dashboard — lists all supported services and providers |
| `GET` | `/start-auth/{service}` | Initiates the OAuth flow for the given service |
| `GET` | `/oauth_callback` | Handles the provider redirect, delivers tokens |
| `POST` | `/refresh` | Refreshes an expired access token |
| `GET` | `/terms` | Terms of Service page |
| `GET` | `/privacy` | Privacy Policy page |

---

## State Parameter

The `state` query parameter passed to `/start-auth/{service}` must be a **base64-encoded JSON object** with the following fields:

| Field | Required | Description |
|-------|----------|-------------|
| `p` | Yes | Provider: `"google"` or `"microsoft"` |
| `r` | Yes | Return URL (webhook endpoint) or `"manual"` to show tokens on screen |
| `u` | No | A user identifier your application uses to correlate the response |

**Example:**

```python
import base64, json

state = base64.urlsafe_b64encode(json.dumps({
    "p": "google",
    "r": "https://your-app.com/webhook/tokens",
    "u": "user_123"
}).encode()).decode()

url = f"https://your-bridge.vercel.app/start-auth/gmail?state={state}"
```

---

## Supported Services & Scopes

### Google

| Service | Scopes Requested |
|---------|-----------------|
| `drive` | `drive`, `drive.file`, `drive.metadata.readonly` |
| `gmail` | `gmail.modify`, `gmail.send`, `gmail.readonly` |
| `calendar` | `calendar`, `calendar.events` |
| `docs` | `documents` |
| `sheets` | `spreadsheets` |
| `slides` | `presentations` |
| `forms` | `forms.body`, `forms.responses.readonly` |
| `chat` | `chat.messages`, `chat.spaces.readonly` |
| `contacts` | `contacts`, `contacts.readonly` |
| `tasks` | `tasks` |
| `all` | All of the above combined |

`openid` and `userinfo.email` are always appended automatically.

### Microsoft

| Service | Scopes Requested |
|---------|-----------------|
| `mail` | `Mail.Read`, `Mail.Send` |
| `onedrive` | `Files.Read`, `Files.ReadWrite.All` |
| `calendar` | `Calendars.Read`, `Calendars.ReadWrite` |
| `contacts` | `Contacts.Read` |

`User.Read` and `offline_access` are always appended automatically.

---

## Token Payload

On success, the following JSON is delivered to the webhook (or shown on screen for manual mode):

```json
{
  "status": "success",
  "provider": "google",
  "user_id": "user_123",
  "email": "user@example.com",
  "credentials": {
    "access_token": "ya29.xxx",
    "refresh_token": "1//xxx",
    "expires_at": 1746000000.0
  }
}
```

---

## Refresh Endpoint

Send a `POST` to `/refresh` with a JSON body to get a new access token:

```json
{
  "provider": "google",
  "refresh_token": "1//xxx"
}
```

The response is the raw token response from the provider (includes a new `access_token` and `expires_in`).

---

## Environment Variables

Create a `.env` file at the project root (for local development) or set these as environment variables in your deployment:

```env
# Google OAuth App Credentials
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Microsoft OAuth App Credentials
MS_CLIENT_ID=your_microsoft_client_id
MS_CLIENT_SECRET=your_microsoft_client_secret

# The callback URL registered in both provider consoles
REDIRECT_URI=https://your-domain.com/oauth_callback

# Optional — only needed for local development
PORT=3000
```
## Setting Up OAuth Apps

### Google Cloud Console

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project.
2. Enable the APIs for the services you need (Gmail API, Drive API, etc.).
3. Navigate to **APIs & Services > Credentials > Create Credentials > OAuth 2.0 Client ID**.
4. Set **Authorized redirect URIs** to your `REDIRECT_URI` value.
5. Copy the **Client ID** and **Client Secret** into your environment.
6. On the **OAuth consent screen**, add the scopes you intend to use.

### Microsoft Entra (Azure AD)

1. Go to [portal.azure.com](https://portal.azure.com) and open **App registrations > New registration**.
2. Set the **Redirect URI** to your `REDIRECT_URI` value (Web platform).
3. Under **Certificates & secrets**, create a new client secret.
4. Under **API permissions**, add the Microsoft Graph permissions you need.
5. Copy the **Application (client) ID** and the client secret value into your environment.

---

> The `.env` file is loaded automatically via `python-dotenv`. It is intentionally excluded from the Docker image; pass variables via `-e` flags or `docker-compose` instead.

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Create your .env file (see above), then run:
python index.py
```

The server starts on `http://localhost:3000` by default.

---

## Docker

```bash
# Build
docker build -t open-auth-bridge .

# Run (pass env vars explicitly)
docker run -p 3000:3000 \
  -e GOOGLE_CLIENT_ID=... \
  -e GOOGLE_CLIENT_SECRET=... \
  -e MS_CLIENT_ID=... \
  -e MS_CLIENT_SECRET=... \
  -e REDIRECT_URI=https://your-domain.com/oauth_callback \
  open-auth-bridge
```

---

## Deploying to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/open-auth-bridge&env=GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET,MS_CLIENT_ID,MS_CLIENT_SECRET,REDIRECT_URI&envDescription=OAuth%20credentials%20for%20Google%20and%20Microsoft%20providers&envLink=https://github.com/your-username/open-auth-bridge%23environment-variables&project-name=open-auth-bridge&repository-name=open-auth-bridge)

The project includes a `vercel.json` that routes all traffic through `api/index.py` using the `@vercel/python` runtime.

```bash
vercel deploy
```

Set the environment variables listed above in your Vercel project settings (**Settings > Environment Variables**). Make sure `REDIRECT_URI` matches the callback URL you registered in the Google Cloud Console and Microsoft Entra (Azure AD) app registration.

---


## Dependencies

| Package | Purpose |
|---------|---------|
| `aiohttp` | Async HTTP server and client |
| `google-auth-oauthlib` | Google OAuth 2.0 helpers |
| `python-dotenv` | Load environment variables from `.env` |

---

## License

MIT — see [Arshman](https://arshman.me) for contact information.
