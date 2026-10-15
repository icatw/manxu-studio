from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import require_rate_limit
from app.core.security import check_csrf
from app.db.session import get_session
from app.services import auth_service
from app.services.auth_service import (
    AccountProfileUpdate,
    AccountView,
    CsrfTokenView,
    EmailCodeRequest,
    EmailVerifyRequest,
    IdentityView,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
SessionDep = Depends(get_session)


@router.get("/csrf", operation_id="getCsrfToken", response_model=CsrfTokenView)
async def get_csrf_token(
    request: Request, response: Response, session: AsyncSession = SessionDep
) -> CsrfTokenView:
    return await auth_service.get_csrf_token(request, response, session)


@router.post(
    "/email/code",
    operation_id="requestEmailCode",
    dependencies=[Depends(require_rate_limit)],
)
async def request_email_code(
    body: EmailCodeRequest, session: AsyncSession = SessionDep
) -> dict[str, str]:
    return await auth_service.request_email_code(body, session)


@router.post(
    "/email/verify", operation_id="verifyEmailCode", dependencies=[Depends(require_rate_limit)]
)
async def verify_email_code(
    body: EmailVerifyRequest, response: Response, session: AsyncSession = SessionDep
) -> AccountView:
    return await auth_service.verify_email_code(body, response, session)


@router.get(
    "/github/start",
    operation_id="startGitHubLogin",
)
async def start_github_login(session: AsyncSession = SessionDep) -> RedirectResponse:
    return await auth_service.start_github_login(session)


@router.get(
    "/github/callback",
    operation_id="completeGitHubLogin",
)
async def github_callback(
    request: Request, response: Response, session: AsyncSession = SessionDep
) -> RedirectResponse:
    return await auth_service.github_callback(request, response, session)


@router.get("/me", operation_id="getCurrentAccount", response_model=AccountView)
async def get_current_account(
    request: Request, session: AsyncSession = SessionDep
) -> AccountView:
    return await auth_service.get_current_account(request, session)


@router.patch("/me", operation_id="updateCurrentAccount", response_model=AccountView)
async def update_current_account(
    body: AccountProfileUpdate, request: Request, session: AsyncSession = SessionDep
) -> AccountView:
    check_csrf(request)
    return await auth_service.update_current_account(body, request, session)


@router.get("/identities", operation_id="listAuthIdentities", response_model=list[IdentityView])
async def list_auth_identities(
    request: Request, session: AsyncSession = SessionDep
) -> list[IdentityView]:
    return await auth_service.list_auth_identities(request, session)


@router.delete("/identities/{identity_id}", operation_id="deleteAuthIdentity", status_code=204)
async def delete_auth_identity(
    identity_id: str, request: Request, response: Response, session: AsyncSession = SessionDep
) -> Response:
    check_csrf(request)
    return await auth_service.delete_auth_identity(identity_id, request, response, session)


@router.post("/logout", operation_id="logout", status_code=204)
async def logout(
    request: Request, response: Response, session: AsyncSession = SessionDep
) -> Response:
    # CSRF is enforced inside the service only for still-valid cookie sessions.
    return await auth_service.logout(request, response, session)
