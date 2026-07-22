from time import sleep

from fastapi import APIRouter

from app.schemas.loyalty import LoyaltyHistoryResponse, LoyaltyResponse

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


# TODO: MOCK
@router.get("", response_model=LoyaltyResponse)
def get_points():
    sleep(1)
    return LoyaltyResponse(balance=17_000)


# TODO: MOCK
# TODO: Use current user
@router.get("/history", response_model=LoyaltyHistoryResponse)
def get_points_history():
    items = [
        {"id": 1, "created_at": "2026-01-12T10:15:00", "amount": 120, "order_id": 101},
        {"id": 2, "created_at": "2026-01-19T14:30:00", "amount": 80, "order_id": 104},
        {"id": 3, "created_at": "2026-02-03T09:05:00", "amount": -50, "order_id": 104},
        {"id": 4, "created_at": "2026-02-18T16:45:00", "amount": 200, "order_id": 112},
        {"id": 5, "created_at": "2026-03-01T11:20:00", "amount": 75, "order_id": 118},
        {"id": 6, "created_at": "2026-03-14T13:10:00", "amount": -100, "order_id": 121},
        {"id": 7, "created_at": "2026-03-28T08:50:00", "amount": 160, "order_id": 126},
        {"id": 8, "created_at": "2026-04-09T17:25:00", "amount": 90, "order_id": 133},
        {"id": 9, "created_at": "2026-04-22T12:00:00", "amount": -75, "order_id": 136},
        {"id": 10, "created_at": "2026-05-06T15:40:00", "amount": 240, "order_id": 141},
        {"id": 11, "created_at": "2026-05-21T10:35:00", "amount": 110, "order_id": 147},
        {
            "id": 12,
            "created_at": "2026-06-02T18:15:00",
            "amount": -120,
            "order_id": 149,
        },
        {"id": 13, "created_at": "2026-06-17T09:45:00", "amount": 180, "order_id": 155},
        {"id": 14, "created_at": "2026-07-04T14:05:00", "amount": 130, "order_id": 162},
        {"id": 15, "created_at": "2026-07-19T11:55:00", "amount": -60, "order_id": 162},
    ]

    sleep(1)
    return LoyaltyHistoryResponse(
        items=items, balance=sum(item["amount"] for item in items)
    )
