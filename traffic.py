import aiohttp
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ========== ТОШКЕНТ АСОСИЙ ЙЎЛЛАРИ ==========
# 2GIS координаталари: x=longitude, y=latitude

TOSHKENT_ROUTES = [
    {
        "name": "Чилонзор — Марказ",
        "points": [{"x": 69.2401, "y": 41.2995}, {"x": 69.2731, "y": 41.2994}],
        "emoji": "🛣️"
    },
    {
        "name": "Юнусобод — Марказ",
        "points": [{"x": 69.2868, "y": 41.3506}, {"x": 69.2731, "y": 41.2994}],
        "emoji": "🛣️"
    },
    {
        "name": "Яккасарой — Марказ",
        "points": [{"x": 69.2614, "y": 41.2821}, {"x": 69.2731, "y": 41.2994}],
        "emoji": "🛣️"
    },
    {
        "name": "Мирзо Улуғбек — Марказ",
        "points": [{"x": 69.3204, "y": 41.3189}, {"x": 69.2731, "y": 41.2994}],
        "emoji": "🛣️"
    },
    {
        "name": "Сергели — Марказ",
        "points": [{"x": 69.2614, "y": 41.2341}, {"x": 69.2731, "y": 41.2994}],
        "emoji": "🛣️"
    },
    {
        "name": "Учтепа — Марказ",
        "points": [{"x": 69.2201, "y": 41.3012}, {"x": 69.2731, "y": 41.2994}],
        "emoji": "🛣️"
    },
]

# ========== ТИРБАНДЛИК ДАРАЖАСИ ==========

def get_traffic_emoji(score: int) -> str:
    if score <= 2:   return "🟢"
    elif score <= 4: return "🟡"
    elif score <= 6: return "🟠"
    else:            return "🔴"

def get_traffic_label(score: int) -> str:
    if score <= 2:   return "Эркин"
    elif score <= 4: return "Озроқ тирбандлик"
    elif score <= 6: return "Тирбандлик бор"
    elif score <= 8: return "Қаттиқ тирбандлик"
    else:            return "Тўлиқ тиқилиш"

# ========== 2GIS ROUTING API ==========

async def get_route_traffic_2gis(api_key: str, points: list) -> dict:
    """
    2GIS Directions API орқали маршрут маълумоти олиш.
    Тирбандлик билан (jam) ва статистик вақтни солиштириш.
    """
    url = f"https://routing.api.2gis.com/carrouting/6.0.0/global?key={api_key}"
    
    payload_jam = {
        "locale": "ru",
        "points": [{"type": "walking", "x": p["x"], "y": p["y"]} for p in points],
        "type": "jam"  # реал тирбандлик билан
    }
    payload_stat = {
        "locale": "ru", 
        "points": [{"type": "walking", "x": p["x"], "y": p["y"]} for p in points],
        "type": "statistic"  # тирбандликсиз статистик
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Иккита сўров: тирбандлик билан ва тирбандликсиз
            async with session.post(url, json=payload_jam, timeout=aiohttp.ClientTimeout(total=10)) as r1:
                data_jam = await r1.json() if r1.status == 200 else None
            async with session.post(url, json=payload_stat, timeout=aiohttp.ClientTimeout(total=10)) as r2:
                data_stat = await r2.json() if r2.status == 200 else None

        if not data_jam or not data_stat:
            return None

        # Вақтни олиш (секундда)
        dur_jam  = data_jam.get("result", [{}])[0].get("total_duration", 0)
        dur_stat = data_stat.get("result", [{}])[0].get("total_duration", 1)

        if dur_stat == 0:
            return None

        # Тирбандлик коэффициенти
        ratio = dur_jam / dur_stat
        if ratio < 1.1:   score = 1
        elif ratio < 1.3: score = 3
        elif ratio < 1.6: score = 5
        elif ratio < 2.0: score = 7
        else:             score = 9

        return {
            "score": score,
            "duration_min": round(dur_jam / 60),
        }

    except Exception as e:
        logger.error(f"2GIS API хато: {e}")
        return None

# ========== УМУМИЙ ШАҲАР ТИРБАНДЛИГИ ==========

async def get_city_traffic_score(api_key: str) -> dict:
    tasks = [get_route_traffic_2gis(api_key, r["points"]) for r in TOSHKENT_ROUTES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    route_data = []
    total_score, valid_count = 0, 0

    for i, result in enumerate(results):
        route = TOSHKENT_ROUTES[i]
        if result and not isinstance(result, Exception):
            score = result["score"]
            total_score += score
            valid_count += 1
            route_data.append({
                "name": route["name"],
                "score": score,
                "traffic_emoji": get_traffic_emoji(score),
                "label": get_traffic_label(score),
                "duration_min": result["duration_min"],
            })
        else:
            route_data.append({
                "name": route["name"],
                "score": 0,
                "traffic_emoji": "⚪",
                "label": "Маълумот йўқ",
                "duration_min": 0,
            })

    avg_score = round(total_score / valid_count) if valid_count > 0 else 0
    return {
        "avg_score": avg_score,
        "routes": route_data,
        "timestamp": datetime.now().strftime("%H:%M"),
    }

# ========== ХАБАР ФОРМАТЛАШ ==========

def format_traffic_message(data: dict) -> str:
    avg = data["avg_score"]
    time_str = data["timestamp"]
    overall_emoji = get_traffic_emoji(avg)
    overall_label = get_traffic_label(avg)

    lines = [
        f"🚦 <b>Тошкент йўллари</b> | {time_str}",
        f"━━━━━━━━━━━━━━━",
        f"Умумий: {overall_emoji} <b>{overall_label}</b>",
        f"━━━━━━━━━━━━━━━",
    ]
    for route in data["routes"]:
        dur = f" (~{route['duration_min']} дақ)" if route["duration_min"] > 0 else ""
        lines.append(f"{route['traffic_emoji']} <b>{route['name']}</b>\n   └ {route['label']}{dur}")

    lines.append("━━━━━━━━━━━━━━━")
    lines.append("📲 @probka_uz | Хабар: /start")
    return "\n".join(lines)

# ========== ТЕСТ РЕЖИМИ (API КАЛИТСИЗ) ==========

def get_mock_traffic_data() -> dict:
    import random
    hour = datetime.now().hour
    if hour in [7, 8, 9]:       base = random.randint(6, 9)
    elif hour in [17, 18, 19]:  base = random.randint(7, 10)
    elif hour in [12, 13]:      base = random.randint(4, 6)
    else:                       base = random.randint(1, 4)

    routes = []
    for route in TOSHKENT_ROUTES:
        score = max(1, min(10, base + random.randint(-2, 2)))
        routes.append({
            "name": route["name"],
            "score": score,
            "traffic_emoji": get_traffic_emoji(score),
            "label": get_traffic_label(score),
            "duration_min": random.randint(10, 45),
        })
    return {
        "avg_score": base,
        "routes": routes,
        "timestamp": datetime.now().strftime("%H:%M"),
    }
