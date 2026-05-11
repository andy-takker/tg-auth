from abc import ABC, abstractmethod

from tg_auth.domains.entities.tokens import TokenPair
from tg_auth.domains.entities.user import UserID


class InvalidTokenError(Exception):
    """Raised by ``ITokenIssuer`` when a presented token cannot be trusted —
    bad signature, expired, wrong type, malformed claims."""


class ITokenIssuer(ABC):
    """Issues + validates the access/refresh JWT pair.

    Stateless by design: validation never touches a store, so any process
    holding the signing secret can verify a token. Use a stateful
    implementation if you need server-side revocation.
    """

    @abstractmethod
    def issue_pair(self, user_id: UserID) -> TokenPair:
        pass

    @abstractmethod
    def validate_access(self, token: str) -> UserID:
        """Return the user_id encoded in an ``access`` token, or raise
        :class:`InvalidTokenError`."""
        pass

    @abstractmethod
    def validate_refresh(self, token: str) -> UserID:
        """Return the user_id encoded in a ``refresh`` token, or raise
        :class:`InvalidTokenError`."""
        pass
