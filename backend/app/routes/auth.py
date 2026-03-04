from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from app.core.config import settings
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    UserResponse,
    DailyBonusStatusResponse,
    DailyBonusClaimResponse,
)
from app.utils.time import utc_now

router = APIRouter()

# ── Daily bonus constants ──────────────────────────────────────────────────
DAILY_BONUS_BASE = 50  # base bonus amount
DAILY_BONUS_PER_STREAK = 10  # extra per streak day
DAILY_BONUS_MAX = 200  # cap
DAILY_BONUS_COOLDOWN_HOURS = 24
DAILY_BONUS_STREAK_WINDOW_HOURS = 48  # streak resets after this


def _calc_bonus_amount(streak: int) -> float:
    """Calculate bonus for the given streak level."""
    return min(DAILY_BONUS_BASE + (streak * DAILY_BONUS_PER_STREAK), DAILY_BONUS_MAX)


def _bonus_status(user: User):
    """Return (available, next_streak, bonus_amount, next_available_at)."""
    now = utc_now()
    if user.last_daily_bonus is None:
        return True, 1, _calc_bonus_amount(0), None

    hours_since = (now - user.last_daily_bonus).total_seconds() / 3600

    if hours_since < DAILY_BONUS_COOLDOWN_HOURS:
        # Not yet available
        next_at = user.last_daily_bonus + timedelta(hours=DAILY_BONUS_COOLDOWN_HOURS)
        streak = user.daily_bonus_streak
        return False, streak, _calc_bonus_amount(streak), next_at

    # Available — check streak continuity
    if hours_since <= DAILY_BONUS_STREAK_WINDOW_HOURS:
        next_streak = user.daily_bonus_streak + 1
    else:
        next_streak = 1  # streak reset

    return True, next_streak, _calc_bonus_amount(next_streak - 1), None


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("5/minute")
def register(request: Request, user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user exists (email already normalized by schema)
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        balance=settings.INITIAL_BALANCE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    # Find user
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/daily-bonus", response_model=DailyBonusStatusResponse)
def daily_bonus_status(current_user: User = Depends(get_current_user)):
    """Check if the daily bonus is available."""
    available, streak, amount, next_at = _bonus_status(current_user)
    return DailyBonusStatusResponse(
        available=available,
        streak=streak,
        bonus_amount=amount,
        next_available_at=next_at,
    )


@router.post("/daily-bonus", response_model=DailyBonusClaimResponse)
def claim_daily_bonus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Claim the daily login bonus."""
    available, streak, amount, _ = _bonus_status(current_user)
    if not available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Daily bonus already claimed. Come back later!",
        )

    current_user.balance = float(current_user.balance) + amount
    current_user.daily_bonus_streak = streak
    current_user.last_daily_bonus = utc_now()
    db.commit()
    db.refresh(current_user)

    return DailyBonusClaimResponse(
        bonus_amount=amount,
        new_balance=float(current_user.balance),
        streak=streak,
        message=f"Day {streak} bonus! +${amount:.0f}",
    )
