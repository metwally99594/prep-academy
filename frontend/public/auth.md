# Auth.md

## Prep Academy API authentication

The public API is documented at `https://prep-academy.onrender.com/openapi.json`.

## Current authentication flow

1. Create an account with `POST /api/auth/register`.
2. Verify the email address sent by the service.
3. Sign in with `POST /api/auth/login`.
4. Send the returned JWT in the `Authorization: Bearer <token>` header.

The API currently uses application JWT authentication rather than OAuth/OIDC. There is no agent self-registration or delegated OAuth authorization server at this time; clients must use an account created through the normal registration flow.

Health endpoint: `https://prep-academy.onrender.com/api/health`
