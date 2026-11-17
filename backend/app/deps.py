"""Request dependencies: who is calling, and may they touch this workspace?"""
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Path, status

from app.auth import CurrentUser, get_current_user
from app.services.workspaces import ADMIN_ROLES, get_role


@dataclass(frozen=True)
class Membership:
    workspace_id: str
    user: CurrentUser
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role in ADMIN_ROLES


def require_member(
    workspace_id: UUID = Path(..., description="Workspace ID"),
    user: CurrentUser = Depends(get_current_user),
) -> Membership:
    """Caller must be a member of the workspace in the path.

    Non-members get 404, not 403, so workspace IDs can't be probed for
    existence.
    """
    role = get_role(str(workspace_id), user.id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return Membership(workspace_id=str(workspace_id), user=user, role=role)


def require_admin(membership: Membership = Depends(require_member)) -> Membership:
    if not membership.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace admin role required")
    return membership
