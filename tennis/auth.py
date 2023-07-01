"""Authentication."""

from dataclasses import dataclass


@dataclass
class TennisAuth:
    """Struct for tennis authentication."""

    role_id: str

    def get_role_id(self) -> str:
        """Get role ID authentication."""
        return ''
