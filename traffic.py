import aiohttp
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ========== ТОШКЕНТ АСОСИЙ ЙЎЛЛАРИ ==========
# (Координаталар: бошланиш → охир нуқтаси)

TOSHKENT_ROUTES = [
    {
        "name": "Чилонзор — Марказ",
        "from": "41.2995,69.2401",
        "to": "41.2994,69.2731",
        "emoji": "🛣️"
    },
    {
        "name": "Юнусобод — Марказ",
        "from": "41.3506,69.2868",
        "to": "41.2994,69.2731",
        "emoji": "🛣️"
    },
    {
        "name": "Яккасарой — Марказ",
        "from": "41.2821,69.2614",
        "to": "41.2994,69.2731",
        "emoji": "🛣️"
    },
    {
        "name": "Мирзо Улуғбек — Марказ",
        "from": "41.3189,69.3204",
        "to": "41.2994,69.2731",
        "emoji": "🛣️"
    },
    {
        "name": "Сергели — Марказ",
        "from": "41.2341,69.2614",
        "to": "41.2994,69.2731",
        "emoji": "🛣️"
    },
    {
        "name": "Учтепа — Марказ",
        "from": "41.3012,69.2201",
        "to": "41.2994,69.2731",
        "emoji": "🛣️"
    },
]

# ========== ТИРБАНдЛИК ДАРАЖАСИ ==========

def get_traffic_emoji(score: int) -> str:
    """Тирбандлик баллига кўра эмодзи"""
    if score <= 2:
        return "🟢"
    elif score <= 4:
        return "🟡"
    elif score <= 6:
        return "🟠"
    else:
        return "🔴"

def get_traffic_label(score: int) -> str:
    """Тирбандлик баллига кўра ёрлиқ"""
    if score <= 2:
        return "Эркин"
    elif score <= 4:
        return "Озроқ тирбандлик"
    elif score <= 6:
        return "Тирбандлик бор"
    elif score <= 8:
        return "Қаттиқ тирбандлик"
    else:
        return "Тўлиқ тиқилиш"

# ========== ЯНДЕКС ROUTER API ==========

async def get_route_traffic(
    api_key: str,
    from_coords: str,
    to_coords: str
) -> dict:
    """
    Яндекс Router API орқали маршрут вақтини олиш.
    Тирбандлик билан ва тирбандликсиз вақтни солиштириш орқали
    тирбандлик даражасини аниқлаш.
    """
    url = "https://router.yandex.ru/v2/route"
    params = {
        "apikey": api_key,
        "waypoints": f"{from_coords}|{to_coords}",
        "mode": "driving",
        "avoid_tolls": "false",
        "lang": "ru_RU",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return parse_route_response(data)
                else:
                    logger.error(f"Яндекс API хато: {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"Яндекс API уланишда хато: {e}")
        return None

def parse_route_response(data: dict) -> dict:
    """API жавобидан керакли маълумотни олиш"""
    try:
        route = data["route"]["legs"][0]
        duration_with_jams = route["duration"]["value"]  # секунд
        duration_no_jams = route.get("duration_in_traffic", {}).get("value", duration_with_jams)

        # Тирбандлик коэффициенти
        ratio = duration_with_jams / max(duration_no_jams, 1)
        
        # 1-10 шкалага ўгириш
        if ratio < 1.1:
            score = 1
        elif ratio < 1.3:
            score = 3
        elif ratio < 1.6:
            score = 5
        elif ratio < 2.0:
            score = 7
        else:
            score = 9

        return {
            "duration_min": round(duration_with_jams / 60),
            "score": score,
        }
    except Exception as e:
        logger.error(f"Жавобни таҳлил қилишда хато: {e}")
        return None

# ========== УМУМИЙ ШАҲАР ТИРБАНДЛИГИ ==========

async def get_city_traffic_score(api_key: str) -> dict:
    """
    Барча асосий йўллар бўйича ўртача тирбандлик баллини ҳисоблаш
    """
    tasks = []
    for route in TOSHKENT_ROUTES:
        tasks.append(
            get_route_traffic(api_key, route["from"], route["to"])
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    route_data = []
    total_score = 0
    valid_count = 0

    for i, result in enumerate(results):
        route = TOSHKENT_ROUTES[i]
        if result and not isinstance(result, Exception):
            score = result["score"]
            total_score += score
            valid_count += 1
            route_data.append({
                "name": route["name"],
                "emoji": route["emoji"],
                "score": score,
                "traffic_emoji": get_traffic_emoji(score),
                "label": get_traffic_label(score),
                "duration_min": result["duration_min"],
            })
        else:
            route_data.append({
                "name": route["name"],
                "emoji": route["emoji"],
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
    """Тирбандлик маълумотини Телеграм хабарига айлантириш"""
    avg = data["avg_score"]
    time_str = data["timestamp"]

    overall_emoji = get_traffic_emoji(avg)
    overall_label = get_traffic_label(avg)

    lines = [
        f"🚦 <b>Тошкент йўллари</b> | {time_str}",
        f"━━━━━━━━━━━━━━━",
        f"Умумий баҳо: {overall_emoji} <b>{overall_label}</b> ({avg}/10)",
        f"━━━━━━━━━━━━━━━",
    ]

    for route in data["routes"]:
        lines.append(
            f"{route['traffic_emoji']} <b>{route['name']}</b>\n"
            f"   └ {route['label']}"
            + (f" (~{route['duration_min']} дақ)" if route['duration_min'] > 0 else "")
        )

    lines.append("━━━━━━━━━━━━━━━")
    lines.append("📲 @probka_uz | Хабар юбориш: /start")

    return "\n".join(lines)

# ========== ТЕСТ ФУНКЦИЯСИ (API КАЛИТСИЗ) ==========

def get_mock_traffic_data() -> dict:
    """
    API калити бўлмаганда тест учун.
    Реал ишлатишда get_city_traffic_score() ишлатинг.
    """
    import random
    hour = datetime.now().hour
    
    # Тонг ва кечки тиқилиш вақтлари
    if hour in [7, 8, 9]:
        base_score = random.randint(6, 9)
    elif hour in [17, 18, 19]:
        base_score = random.randint(7, 10)
    elif hour in [12, 13]:
        base_score = random.randint(4, 6)
    else:
        base_score = random.randint(1, 4)

    routes = []
    for route in TOSHKENT_ROUTES:
        score = max(1, min(10, base_score + random.randint(-2, 2)))
        routes.append({
            "name": route["name"],
            "emoji": route["emoji"],
            "score": score,
            "traffic_emoji": get_traffic_emoji(score),
            "label": get_traffic_label(score),
            "duration_min": random.randint(10, 45),
        })

    return {
        "avg_score": base_score,
        "routes": routes,
        "timestamp": datetime.now().strftime("%H:%M"),
    }
