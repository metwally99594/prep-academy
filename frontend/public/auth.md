# Auth.md

## Prep Academy API authentication

The public API is documented at `https://prep-academy.onrender.com/openapi.json`.

## Current authentication flow

1. Create an account with `POST /api/auth/register`.
2. Verify the email address sent by the service.
3. Sign in with `POST /api/auth/login`.
4. Send the returned JWT in the `Authorization: Bearer <token>` header.

The API currently uses application JWT authentication rather than OAuth/OIDC. There is no agent self-registration or delegated OAuth authorization server at this time; clients must use an account created through the normal registration flow.

## Agent registration

Agents may register an account through the same public registration endpoint:

```http
POST https://prep-academy.onrender.com/api/auth/register
Content-Type: application/json
```

Send the registration payload accepted by the API, then complete the email verification step. After verification, call `POST /api/auth/login` and use the returned JWT as `Authorization: Bearer <token>` for protected API requests. The service does not currently issue OAuth client credentials or support delegated agent registration.

Health endpoint: `https://prep-academy.onrender.com/api/health`
