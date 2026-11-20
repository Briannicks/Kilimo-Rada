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