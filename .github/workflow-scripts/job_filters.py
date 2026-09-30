"""Title, location, term and sponsorship filters shared by every source.

Target profile (Waterloo co-op, needs US work sponsorship):
- software, data/ML, design/systems/hardware, product, and "opportunistic"
  tech roles (quant dev, fintech, business analyst, solutions/support eng);
- the title must say intern / co-op / student / fellow / apprentice;
- US, Canada or remote; a posting that requires US citizenship is dropped.
"""

import re

INTERN_RE = re.compile(
    r"\bintern(ship)?s?\b|\bco[- ]?ops?\b|\bco-?operative\b|\bstudent\b|"
    r"\bfellow(ship)?\b|\bapprentice(ship)?\b",
    re.I,
)

# Titles that are not a fit even when they say "intern".
TITLE_EXCLUDE_RE = re.compile(
    r"\bsenior\b|\bsr\.?\b|\bstaff\b|\bprincipal\b|\bdirector\b|\bvp\b|\bhead of\b|"
    r"\bvice president\b|\bph\.?d\.?\b|\bpostdoc|\bmba\b|\bmaster'?s\b|\bhigh school\b|"
    r"\bcontract\b|\bpart[- ]time\b|\btemporary\b|\bstudent worker\b",
    re.I,
)

ROLE_RE = re.compile(
    # Software
    r"\bsoftware\b|\bsde\b|\bswe\b|\bdevelopers?\b|\bfull[- ]?stack\b|\bfront[- ]?end\b|"
    r"\bback[- ]?end\b|\bweb\b|\bapplication\b|\bmobile\b|\bios\b|\bandroid\b|\bsdet\b|"
    r"\bqa\b|\bdevops\b|\bsre\b|\bcloud\b|\binfrastructure\b|\bplatform engineer|"
    r"\bsecurity engineer|\bembedded\b|\bfirmware\b|"
    # Data / ML
    r"\bdata (analy|scien|engineer)|\bbusiness intelligence\b|\bbi (analyst|developer)\b|"
    r"\bmachine learning\b|\bml\b|\bai\b|\bartificial intelligence\b|"
    r"\bdeep learning\b|\bnlp\b|"
    # Design / systems / hardware
    r"\bproduct design\b|\bmechanical\b|\bsystems? engineer|\bprototyp|\bmechatronic|"
    r"\brobotics?\b|"
    # Product
    r"\bproduct manage|\bapm\b|\btechnical product\b|\bproduct analyst\b|"
    r"\bproduct (operations|strategy)\b|"
    # Opportunistic
    r"\bquant(itative)?\b|\bfintech\b|\bbusiness analyst\b|\btechnical consult|"
    r"\bsolutions? engineer|\btechnical support\b|\bsupport engineer|\bcustomer engineer|"
    r"\bsales engineer|\bforward deployed\b",
    re.I,
)


def wanted_title(title: str) -> bool:
    return bool(
        INTERN_RE.search(title)
        and not TITLE_EXCLUDE_RE.search(title)
        and ROLE_RE.search(title)
    )


# ---- location -------------------------------------------------------------

US_CODES = (
    r"AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|"
    r"MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY"
)

US_STRONG_RE = re.compile(
    r"united states|\busa?\b|u\.s\.|remote.*\b(us|usa|america)\b|"
    r"alabama|alaska|arizona|arkansas|california|colorado|connecticut|"
    r"delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|"
    r"kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|"
    r"mississippi|missouri|montana|nebraska|nevada|new hampshire|"
    r"new jersey|new mexico|new york|north carolina|north dakota|ohio|"
    r"oklahoma|oregon|pennsylvania|rhode island|south carolina|"
    r"south dakota|tennessee|texas|utah|vermont|virginia|washington|"
    r"west virginia|wisconsin|wyoming|"
    r"san francisco|\bnyc\b|seattle|austin|boston|chicago|denver|atlanta|"
    r"los angeles|mountain view|palo alto|sunnyvale|san jose|menlo park|"
    r"bellevue|redmond|\bd\.?c\.?\b|miami|dallas|houston|philadelphia|"
    r"pittsburgh|portland|san diego|santa clara|cupertino|irvine|"
    r"nashville|charlotte|phoenix|salt lake",
    re.I,
)
US_CODE_RE = re.compile(r",\s?(?-i:" + US_CODES + r")\b")

CANADA_RE = re.compile(
    r"canada|ontario|toronto|vancouver|montr[eé]al|quebec|qu[eé]bec|calgary|ottawa|"
    r"waterloo|kitchener|mississauga|markham|burnaby|edmonton|winnipeg|halifax|"
    r"british columbia|alberta|manitoba|nova scotia|new brunswick|saskatchewan|"
    r",\s?(?-i:ON|QC|BC|AB|MB|SK|NS|NB|NL|PE|YT)\b",
    re.I,
)

OTHER_RE = re.compile(
    r"united kingdom|\buk\b|london|ireland|"
    r"dublin|germany|berlin|munich|france|paris|netherlands|amsterdam|"
    r"belgium|spain|madrid|barcelona|portugal|lisbon|italy|milan|"
    r"switzerland|zurich|geneva|austria|vienna|poland|warsaw|krakow|"
    r"czech|prague|sweden|stockholm|norway|oslo|denmark|copenhagen|"
    r"finland|helsinki|estonia|tallinn|romania|bucharest|hungary|"
    r"budapest|israel|tel aviv|\buae\b|dubai|abu dhabi|saudi|riyadh|"
    r"india|bangalore|bengaluru|hyderabad|mumbai|delhi|gurgaon|gurugram|"
    r"chennai|pune|noida|singapore|malaysia|kuala lumpur|indonesia|"
    r"jakarta|vietnam|thailand|bangkok|philippines|manila|china|beijing|"
    r"shanghai|shenzhen|hangzhou|hong kong|taiwan|taipei|japan|tokyo|"
    r"osaka|korea|seoul|australia|sydney|melbourne|brisbane|new zealand|"
    r"auckland|brazil|paulo|mexico|guadalajara|argentina|buenos aires|"
    r"colombia|bogot|chile|santiago|nigeria|lagos|egypt|cairo|kenya|"
    r"nairobi|south africa|turkey|istanbul|ukraine|kyiv|serbia|belgrade|"
    r"bulgaria|sofia|croatia|zagreb|lithuania|vilnius|latvia|riga|"
    r"armenia|yerevan|cyprus|malta|luxembourg|emea|apac|latam",
    re.I,
)


def regions(location: str) -> set:
    """Return the set of {"US", "CA"} regions a location string points at.

    An empty set means "unknown" (bare "Remote", city-only names, blank) and
    is kept rather than dropped. {"OTHER"} means clearly somewhere else.
    A US state code alone ("Pune, IN") loses to a clearly foreign hint.
    """
    if not location:
        return set()
    found = set()
    if US_STRONG_RE.search(location):
        found.add("US")
    if CANADA_RE.search(location):
        found.add("CA")
    if not found and US_CODE_RE.search(location):
        if OTHER_RE.search(location):
            return {"OTHER"}
        found.add("US")
    if not found and OTHER_RE.search(location):
        return {"OTHER"}
    return found


# ---- term (season + year) --------------------------------------------------

_SEASONS = r"winter|spring|summer|fall|autumn"
SEASON_RE = re.compile(r"\b(" + _SEASONS + r")\b\W{0,3}(?:term\W{0,3})?(?:(20\d\d|['’]\d\d|2[6-9])\b)?", re.I)
YEAR_FIRST_RE = re.compile(r"\b(20\d\d)\s+(" + _SEASONS + r")\b", re.I)
YEAR_RE = re.compile(r"\b(20[2-3]\d)\b")
# "may" is a common word, so months only count with a year or an end month.
MONTH_RE = re.compile(
    r"\b(jan(?:uary)?|may)\b\.?\s*(?:(?:[-–—]|to)\s*(?:apr(?:il)?|aug(?:ust)?)\b\.?\s*,?\s*(20\d\d)?|,?\s*(20\d\d)\b)",
    re.I,
)


def _year(raw):
    """"2027", "'27" or "27" -> 2027; None when absent."""
    if not raw:
        return None
    digits = raw.lstrip("'’")
    return int(digits) if len(digits) == 4 else 2000 + int(digits)


def term_hints(text: str) -> set:
    """Extract {(season, year_or_None)} mentions from a title or terms cell."""
    if not text:
        return set()
    years = set(YEAR_RE.findall(text))
    lone_year = int(next(iter(years))) if len(years) == 1 else None
    hints = set()
    for m in SEASON_RE.finditer(text):
        season = m.group(1).lower().replace("autumn", "fall")
        hints.add((season, _year(m.group(2)) or lone_year))
    for m in YEAR_FIRST_RE.finditer(text):
        hints.add((m.group(2).lower().replace("autumn", "fall"), int(m.group(1))))
    for m in MONTH_RE.finditer(text):
        season = "winter" if m.group(1).lower().startswith("jan") else "summer"
        year = m.group(2) or m.group(3)
        hints.add((season, int(year) if year else lone_year))
    return hints


def term_years(text: str) -> set:
    return {int(y) for y in YEAR_RE.findall(text or "")}


# ---- sponsorship -----------------------------------------------------------

# Only citizenship requirements block a posting. "No sponsorship" language is
# deliberately NOT filtered: those roles still get through.
CITIZEN_ONLY_RE = re.compile(
    r"u\.?s\.?\s+citizen(?:ship)?\s+(?:is\s+|are\s+)?(?:required|only|needed)|"
    r"must\s+be\s+(?:an?\s+)?(?:u\.?s\.?|united states)\s+(?:citizen|person)|"
    r"(?:u\.?s\.?|united states)\s+citizens?\s+only|"
    r"security clearance|itar|export[- ]control(?:led)?",
    re.I,
)
CITIZEN_ONLY_MARKERS = ("🇺🇸",)  # Simplify's "requires US citizenship" flag


def sponsorship_blocked(text: str) -> bool:
    """True only when the posting requires US citizenship (or a clearance,
    which implies it). Everything else, including "no sponsorship", passes."""
    if not text:
        return False
    if any(mark in text for mark in CITIZEN_ONLY_MARKERS):
        return True
    return bool(CITIZEN_ONLY_RE.search(text))
