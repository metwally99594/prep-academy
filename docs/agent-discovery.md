# Agent discovery deployment notes

The website now publishes:

- `/.well-known/api-catalog` as an RFC 9264 linkset.
- `/.well-known/agent-skills/index.json` with SHA-256 skill digests.
- `/.well-known/mcp/server-card.json` for the browser-local WebMCP surface.
- `/auth.md` describing the current JWT authentication flow.
- Markdown negotiation for `/` when the request includes `Accept: text/markdown`.

## DNS-AID

DNS-AID records cannot be published from this repository. They must be added at the authoritative DNS provider and signed with DNSSEC. The intended records are:

```dns
_index._agents.prepacademy-med.com. IN HTTPS 1 . alpn="h2" endpoint="https://prepacademy-med.com/.well-known/api-catalog"
_a2a._agents.prepacademy-med.com.   IN HTTPS 1 . alpn="h2" endpoint="https://prepacademy-med.com/.well-known/api-catalog"
```

Confirm the provider supports the draft DNS-AID `endpoint` parameter before publishing these records. Do not treat this example as active DNS until it is added and DNSSEC validation succeeds.

## OAuth/OIDC

The API currently uses application JWTs returned by `/api/auth/login`; it does not have an OAuth/OIDC authorization server, JWKS endpoint, delegated consent flow, or agent registration endpoint. OAuth discovery documents are intentionally not fabricated. When an identity provider is selected, publish its issuer metadata and protected-resource metadata together with the provider's real endpoints.
