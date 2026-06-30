import os

OWNER_ID = int(os.getenv("OWNER_ID", 0))
DEVELOPER_ID = int(os.getenv("DEVELOPER_USER_ID", 0))

def is_owner(user_id):
    return user_id == OWNER_ID or user_id == DEVELOPER_ID
