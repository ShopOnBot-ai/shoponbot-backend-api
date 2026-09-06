from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.database import get_db
from app.schemas.user import OnboardingMessageResponse, OnboardingRequest, UserPublic
from app.services.aws_service import generate_signed_url

router = APIRouter()


@router.get("/me", response_model=UserPublic, status_code=status.HTTP_200_OK)
async def get_current_user(current_user: CurrentUser):
    user = UserPublic.model_validate(current_user)
    if user.image_url:
        user.image_url = generate_signed_url(user.image_url)

    return user


@router.post(
    "/onboarding", response_model=OnboardingMessageResponse, status_code=status.HTTP_201_CREATED
)
async def onboarding(
    payload: OnboardingRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    full_name = payload.full_name.strip()

    if current_user.onboarding_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Onboarding already completed"
        )

    #  After complete onboarding we'll get the first charecter from full_name and display in frontend as avatar

    current_user.full_name = full_name
    current_user.onboarding_status = True

    return {"message": "Onboarding completed successfully"}
