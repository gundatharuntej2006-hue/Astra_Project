"""IP geolocation via IPStack. Cached per attack type to conserve API credits."""
import logging
import random

import requests

from backend.config import IPSTACK_API_KEY
from backend.constants import REGION_IPS

logger = logging.getLogger("soc.geo")

_GEO_CACHE = {}


def geolocate_attack(attack_type):
    """Resolve an attack type to {lat, lng, city, country, ip} or None."""
    if not IPSTACK_API_KEY:
        return None

    if attack_type in _GEO_CACHE:
        # Jitter so repeated markers don't stack on top of each other.
        cached = _GEO_CACHE[attack_type].copy()
        cached["lat"] += random.uniform(-0.5, 0.5)
        cached["lng"] += random.uniform(-0.5, 0.5)
        return cached

    base_ips = REGION_IPS.get(attack_type, REGION_IPS["Normal"])
    ip = random.choice(base_ips)

    try:
        url = f"https://api.ipstack.com/{ip}?access_key={IPSTACK_API_KEY}"
        resp = requests.get(url, timeout=5).json()
        geo_data = {
            "lat": resp.get("latitude"),
            "lng": resp.get("longitude"),
            "city": resp.get("city"),
            "country": resp.get("country_name"),
            "ip": ip,
        }
        if geo_data["lat"] is not None:
            _GEO_CACHE[attack_type] = geo_data
        return geo_data
    except Exception as e:
        logger.error("Geolocation error: %s", e)
        return None
