
from collections import defaultdict
import asyncio
from datetime import datetime

IDP_CLAIMS = defaultdict(list)

async def cleanup_idp_claims(scrim_id: int, idp_channel_id: int, message_id: int):
    await asyncio.sleep(30 * 60)
    IDP_CLAIMS.pop((scrim_id, idp_channel_id, message_id), None)