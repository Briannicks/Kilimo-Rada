"""Kenya's 47 counties, and a helper that matches what farmers type on USSD."""
import difflib

COUNTIES = (
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa",
    "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi",
    "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos",
    "Makueni", "Mandera", "Marsabit", "Meru", "Migori", "Mombasa", "Murang'a",
    "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri", "Samburu",
    "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans Nzoia", "Turkana",
    "Uasin Gishu", "Vihiga", "Wajir", "West Pokot",
)


# NEW: latitude, longitude of each county's main town (approximate, enough for a weather forecast).
# Used by the USSD weather option, which shows the weather of the county the farmer registered with.
COUNTY_COORDS = {
    "Baringo": (0.49, 35.74), "Bomet": (-0.78, 35.34), "Bungoma": (0.57, 34.56),
    "Busia": (0.46, 34.11), "Elgeyo-Marakwet": (0.67, 35.51), "Embu": (-0.54, 37.46),
    "Garissa": (-0.45, 39.65), "Homa Bay": (-0.53, 34.46), "Isiolo": (0.35, 37.58),
    "Kajiado": (-1.85, 36.78), "Kakamega": (0.28, 34.75), "Kericho": (-0.37, 35.28),
    "Kiambu": (-1.17, 36.83), "Kilifi": (-3.63, 39.85), "Kirinyaga": (-0.50, 37.28),
    "Kisii": (-0.68, 34.77), "Kisumu": (-0.09, 34.77), "Kitui": (-1.37, 38.01),
    "Kwale": (-4.17, 39.45), "Laikipia": (0.01, 37.07), "Lamu": (-2.27, 40.90),
    "Machakos": (-1.52, 37.26), "Makueni": (-1.78, 37.63), "Mandera": (3.94, 41.87),
    "Marsabit": (2.33, 37.99), "Meru": (0.05, 37.65), "Migori": (-1.06, 34.47),
    "Mombasa": (-4.04, 39.67), "Murang'a": (-0.72, 37.15), "Nairobi": (-1.29, 36.82),
    "Nakuru": (-0.30, 36.07), "Nandi": (0.20, 35.10), "Narok": (-1.08, 35.87),
    "Nyamira": (-0.57, 34.95), "Nyandarua": (-0.27, 36.38), "Nyeri": (-0.42, 36.95),
    "Samburu": (1.10, 36.70), "Siaya": (0.06, 34.29), "Taita-Taveta": (-3.40, 38.37),
    "Tana River": (-1.50, 40.03), "Tharaka-Nithi": (-0.33, 37.65), "Trans Nzoia": (1.02, 35.00),
    "Turkana": (3.12, 35.60), "Uasin Gishu": (0.51, 35.27), "Vihiga": (0.08, 34.72),
    "Wajir": (1.75, 40.06), "West Pokot": (1.24, 35.11),
}


def _simplify(text):
    """'  Murang'a County ' -> 'muranga'   (keeps letters only)"""
    text = (text or "").lower().replace("county", "")
    return "".join(ch for ch in text if ch.isalpha())


_LOOKUP = {_simplify(county): county for county in COUNTIES}
# Short names people often type
_LOOKUP.update({
    "elgeyo": "Elgeyo-Marakwet", "marakwet": "Elgeyo-Marakwet",
    "taita": "Taita-Taveta", "taveta": "Taita-Taveta",
    "tharaka": "Tharaka-Nithi", "nithi": "Tharaka-Nithi",
    "nairobicity": "Nairobi", "pokot": "West Pokot",
})


def match_county(text):
    """Turns what a farmer typed on USSD into an official county name, or None.
    'nakuru', 'NAKURU COUNTY', 'muranga', 'homa bay' -> 'Nakuru', ..., "Murang'a", 'Homa Bay'"""
    simple = _simplify(text)
    if len(simple) < 3:
        return None
    if simple in _LOOKUP:
        return _LOOKUP[simple]
    # Small typos: "nakru" -> Nakuru, "kiambo" -> Kiambu
    close = difflib.get_close_matches(simple, _LOOKUP.keys(), n=1, cutoff=0.8)
    return _LOOKUP[close[0]] if close else None