import json

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/user", tags=["user"])

users_file_path = "app/api/mock_users.json"
address_file_path = "app/api/mock_addresses.json"


with open(users_file_path) as f:
    users = json.load(f)["users"]

with open(address_file_path) as f:
    addresses = json.load(f)["addresses"]

for user in users:
    address_id = user.get("address_id")
    if address_id:
        address = next(
            (address for address in addresses if address["id"] == address_id), None
        )
        user["address"] = address


@router.get("/")
async def get_users():
    users_list = [
        [
            user["email"],
            user["address"]["first_name"],
            user["address"]["last_name"],
            user["address"]["city"],
            user["address"]["first_line"],
            user["address"]["second_line"],
            user["address"]["postal_code"],
            user["address"]["country"],
            user["privacy_policy_accepted"],
        ]
        for user in users
    ]
    return jsonable_encoder(users_list)
