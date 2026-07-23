from time import sleep

from fastapi import APIRouter

from app.schemas.cart import PromoCodeValidationRequest, PromoCodeValidationResponse

router = APIRouter(prefix="/cart", tags=["cart"])


# TODO: MOCK
@router.post(
    "/promo-code/validate",
    response_model=PromoCodeValidationResponse,
    summary="Sprawdź kod promocyjny",
    response_description="Wartość rabatu przypisana do kodu promocyjnego",
)
def validate_promo_code(request: PromoCodeValidationRequest):
    if request.promo_code.upper().startswith("D"):
        sleep(1)
    if request.promo_code.upper().endswith("SPORT10"):
        return PromoCodeValidationResponse(discount_rate=0.1)
    return PromoCodeValidationResponse()
