# app/modules/auth_household/utils/oidc_clients.py
import json
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class OIDCClient:
    client_id: str
    redirect_uris: list[str]


class OIDCClientRegistry:
    def __init__(self, clients_json: str = None):
        if clients_json is None:
            clients_json = settings.oidc_clients

        self.clients: dict[str, OIDCClient] = {}
        try:
            parsed = json.loads(clients_json)
            for item in parsed:
                client = OIDCClient(
                    client_id=item["client_id"], redirect_uris=item["redirect_uris"]
                )
                self.clients[client.client_id] = client
        except (json.JSONDecodeError, KeyError, TypeError):
            # Fallback or empty if parsing fails (development robustness)
            pass

    def get_client(self, client_id: str) -> OIDCClient | None:
        return self.clients.get(client_id)

    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        client = self.get_client(client_id)
        if not client:
            return False
        return redirect_uri in client.redirect_uris
