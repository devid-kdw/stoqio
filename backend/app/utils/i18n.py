"""Locale-aware API error message resolution for the WMS backend.

Locale resolution contract (DEC-I18N-001):
  1. Read the primary supported tag from request ``Accept-Language`` header.
  2. If missing or unsupported, fall back to ``SystemConfig.default_language``
     (when a Location row exists and the stored language is supported).
  3. Otherwise fall back to ``hr``.

Only the human-readable ``message`` field is localized.
Machine-readable ``error`` codes, enum values, and field names stay English.

Translation keys
----------------
- For most error codes the key equals the ``error`` code string.
- Service errors may embed a ``_msg_key`` in their ``details`` dict to
  select a more specific template (e.g. ``FIELD_REQUIRED`` for the many
  ``VALIDATION_ERROR`` sub-cases with dynamic field names).  ``_msg_key``
  is stripped from ``details`` before it reaches the API response.
- Template placeholders are filled from the remaining ``details`` values
  using Python str.format_map.  Unknown placeholders are left as-is.
"""

from __future__ import annotations

import re
from typing import Any

from flask import request as flask_request

SUPPORTED_LOCALES: frozenset[str] = frozenset({"hr", "en", "de", "hu"})
_DEFAULT_FALLBACK: str = "hr"

# ---------------------------------------------------------------------------
# Message catalog
# ---------------------------------------------------------------------------
# Each entry maps a translation key to a locale -> template dict.
# Templates may contain {placeholder} tokens resolved from the error details.
# ---------------------------------------------------------------------------

MESSAGES: dict[str, dict[str, str]] = {
    # ── 404 NOT FOUND ───────────────────────────────────────────────────────
    "ARTICLE_NOT_FOUND": {
        "hr": "Artikl nije pronađen.",
        "en": "Article not found.",
        "de": "Artikel nicht gefunden.",
        "hu": "A cikk nem található.",
    },
    "ARTICLE_NOT_FOUND_OR_INACTIVE": {
        "hr": "Artikl nije pronađen ili je neaktivan.",
        "en": "Article not found or inactive.",
        "de": "Artikel nicht gefunden oder inaktiv.",
        "hu": "A cikk nem található vagy inaktív.",
    },
    "EMPLOYEE_NOT_FOUND": {
        "hr": "Zaposlenik nije pronađen.",
        "en": "Employee not found.",
        "de": "Mitarbeiter nicht gefunden.",
        "hu": "Az alkalmazott nem található.",
    },
    "ORDER_NOT_FOUND": {
        "hr": "Narudžba nije pronađena.",
        "en": "Order not found.",
        "de": "Bestellung nicht gefunden.",
        "hu": "A rendelés nem található.",
    },
    "ORDER_LINE_NOT_FOUND": {
        "hr": "Stavka narudžbe nije pronađena.",
        "en": "Order line not found.",
        "de": "Bestellposition nicht gefunden.",
        "hu": "A rendelési sor nem található.",
    },
    "COUNT_NOT_FOUND": {
        "hr": "Popis nije pronađen.",
        "en": "Inventory count not found.",
        "de": "Inventur nicht gefunden.",
        "hu": "A leltár nem található.",
    },
    "LINE_NOT_FOUND": {
        "hr": "Redak popisa nije pronađen.",
        "en": "Count line not found.",
        "de": "Inventurposition nicht gefunden.",
        "hu": "A leltársor nem található.",
    },
    "SUPPLIER_NOT_FOUND": {
        "hr": "Dobavljač nije pronađen.",
        "en": "Supplier not found.",
        "de": "Lieferant nicht gefunden.",
        "hu": "A szállító nem található.",
    },
    "USER_NOT_FOUND": {
        "hr": "Korisnik nije pronađen.",
        "en": "User not found.",
        "de": "Benutzer nicht gefunden.",
        "hu": "A felhasználó nem található.",
    },
    "QUOTA_NOT_FOUND": {
        "hr": "Kvota nije pronađena.",
        "en": "Quota not found.",
        "de": "Kontingent nicht gefunden.",
        "hu": "A kvóta nem található.",
    },
    "CATEGORY_NOT_FOUND": {
        "hr": "Kategorija nije pronađena.",
        "en": "Category not found.",
        "de": "Kategorie nicht gefunden.",
        "hu": "A kategória nem található.",
    },
    "ALIAS_NOT_FOUND": {
        "hr": "Alias nije pronađen.",
        "en": "Alias not found.",
        "de": "Alias nicht gefunden.",
        "hu": "Az álnév nem található.",
    },
    "BATCH_NOT_FOUND": {
        "hr": "Serija nije pronađena za ovaj artikl.",
        "en": "Batch not found for this article.",
        "de": "Charge für diesen Artikel nicht gefunden.",
        "hu": "A tétel nem található ehhez a cikkhez.",
    },
    "MISSING_ARTICLE_REPORT_NOT_FOUND": {
        "hr": "Prijava nedostajućeg artikla nije pronađena.",
        "en": "Missing article report not found.",
        "de": "Fehlender-Artikel-Bericht nicht gefunden.",
        "hu": "A hiányzó cikk jelentés nem található.",
    },
    "NOT_FOUND": {
        "hr": "Resurs nije pronađen.",
        "en": "Resource not found.",
        "de": "Ressource nicht gefunden.",
        "hu": "Az erőforrás nem található.",
    },
    # ── 409 CONFLICT ────────────────────────────────────────────────────────
    "BATCH_EXPIRY_MISMATCH": {
        "hr": "Serija {batch_code} već postoji s drugačijim datumom isteka.",
        "en": "Batch {batch_code} already exists with a different expiry date.",
        "de": "Charge {batch_code} existiert bereits mit einem anderen Ablaufdatum.",
        "hu": "A(z) {batch_code} tétel már létezik eltérő lejárati dátummal.",
    },
    "ARTICLE_ALREADY_EXISTS": {
        "hr": "Artikl s ovim brojem već postoji.",
        "en": "An article with this number already exists.",
        "de": "Ein Artikel mit dieser Nummer existiert bereits.",
        "hu": "Már létezik cikk ezzel a számmal.",
    },
    "ALIAS_ALREADY_EXISTS": {
        "hr": "Alias već postoji.",
        "en": "Alias already exists.",
        "de": "Alias existiert bereits.",
        "hu": "Az álnév már létezik.",
    },
    "EMPLOYEE_ID_EXISTS": {
        "hr": "Šifra zaposlenika već postoji.",
        "en": "Employee ID already exists.",
        "de": "Mitarbeiter-ID existiert bereits.",
        "hu": "Az alkalmazotti azonosító már létezik.",
    },
    "SETUP_ALREADY_COMPLETED": {
        "hr": "Inicijalno postavljanje je već dovršeno.",
        "en": "Initial setup has already been completed.",
        "de": "Die Ersteinrichtung ist bereits abgeschlossen.",
        "hu": "A kezdeti beállítás már befejeződött.",
    },
    "MISSING_ARTICLE_REPORT_CONFLICT": {
        "hr": "Konflikt pri obradi prijave nedostajućeg artikla.",
        "en": "Conflict processing missing article report.",
        "de": "Konflikt bei der Verarbeitung des fehlenden Artikelberichts.",
        "hu": "Ütközés a hiányzó cikk jelentés feldolgozásakor.",
    },
    # ── 400 domain errors ───────────────────────────────────────────────────
    "INSUFFICIENT_STOCK": {
        "hr": "Nedovoljne zalihe za ovu operaciju.",
        "en": "Insufficient stock for this operation.",
        "de": "Nicht ausreichender Bestand für diese Operation.",
        "hu": "Nem elegendő készlet ehhez a művelethez.",
    },
    "ORDER_CLOSED": {
        "hr": "Narudžba je zatvorena.",
        "en": "Order is closed.",
        "de": "Bestellung ist geschlossen.",
        "hu": "A rendelés le van zárva.",
    },
    "ORDER_LINE_REMOVED": {
        "hr": "Stavka narudžbe je uklonjena.",
        "en": "Order line has been removed.",
        "de": "Bestellposition wurde entfernt.",
        "hu": "A rendelési sor el lett távolítva.",
    },
    "ORDER_LINE_CLOSED": {
        "hr": "Stavka narudžbe je već zatvorena.",
        "en": "Order line is already closed.",
        "de": "Bestellposition ist bereits geschlossen.",
        "hu": "A rendelési sor már le van zárva.",
    },
    "BATCH_REQUIRED": {
        "hr": "Za ovaj artikl potrebna je serija.",
        "en": "A batch is required for this article.",
        "de": "Für diesen Artikel ist eine Charge erforderlich.",
        "hu": "Ehhez a cikkhez tétel szükséges.",
    },
    "QUOTA_EXCEEDED": {
        "hr": "Kvota je prekoračena.",
        "en": "Quota exceeded.",
        "de": "Kontingent überschritten.",
        "hu": "A kvóta túllépve.",
    },
    "COUNT_NOT_IN_PROGRESS": {
        "hr": "Popis nije u tijeku.",
        "en": "Count is not in progress.",
        "de": "Inventur ist nicht aktiv.",
        "hu": "A leltár nem folyamatban van.",
    },
    "COUNT_IN_PROGRESS": {
        "hr": "Popis zaliha je već u tijeku.",
        "en": "An inventory count is already in progress.",
        "de": "Eine Inventur läuft bereits.",
        "hu": "Már folyamatban van egy leltár.",
    },
    "OPENING_COUNT_EXISTS": {
        "hr": "Popis otvaranja zaliha već postoji.",
        "en": "Opening stock count already exists.",
        "de": "Eröffnungsbestand-Inventur existiert bereits.",
        "hu": "A nyitókészlet-leltár már létezik.",
    },
    "UOM_NOT_FOUND": {
        "hr": "Jedinica mjere nije pronađena.",
        "en": "UOM not found.",
        "de": "Maßeinheit nicht gefunden.",
        "hu": "A mértékegység nem található.",
    },
    "UOM_MISMATCH": {
        "hr": "Jedinica mjere ne odgovara baznoj jedinici artikla '{expected_uom}'.",
        "en": "uom must match article base UOM '{expected_uom}'.",
        "de": "Maßeinheit muss der Basis-Maßeinheit des Artikels '{expected_uom}' entsprechen.",
        "hu": "A mértékegységnek meg kell egyeznie a cikk alap-mértékegységével: '{expected_uom}'.",
    },
    "SELF_DEACTIVATION_FORBIDDEN": {
        "hr": "Ne možete deaktivirati vlastiti račun.",
        "en": "You cannot deactivate your own account.",
        "de": "Sie können Ihr eigenes Konto nicht deaktivieren.",
        "hu": "Nem deaktiválhatja a saját fiókját.",
    },
    # ── VALIDATION_ERROR sub-keys ────────────────────────────────────────────
    # These are selected via details["_msg_key"] for dynamic VALIDATION_ERROR messages.
    "FIELD_REQUIRED": {
        "hr": "{field} je obavezno.",
        "en": "{field} is required.",
        "de": "{field} ist erforderlich.",
        "hu": "{field} megadása kötelező.",
    },
    "FIELD_TOO_LONG": {
        "hr": "{field} mora imati najviše {max_length} znakova.",
        "en": "{field} must be {max_length} characters or fewer.",
        "de": "{field} darf höchstens {max_length} Zeichen lang sein.",
        "hu": "A(z) {field} legfeljebb {max_length} karakter lehet.",
    },
    "FIELD_NOT_INTEGER": {
        "hr": "{field} mora biti cijeli broj.",
        "en": "{field} must be a valid integer.",
        "de": "{field} muss eine gültige Ganzzahl sein.",
        "hu": "A(z) {field} csak egész szám lehet.",
    },
    "FIELD_NOT_POSITIVE": {
        "hr": "{field} mora biti veći od nule.",
        "en": "{field} must be greater than zero.",
        "de": "{field} muss größer als null sein.",
        "hu": "A(z) {field} értéknek nullánál nagyobbnak kell lennie.",
    },
    "FIELD_NOT_NUMBER": {
        "hr": "{field} mora biti broj.",
        "en": "{field} must be a valid number.",
        "de": "{field} muss eine gültige Zahl sein.",
        "hu": "A(z) {field} csak szám lehet.",
    },
    "FIELD_GTE_ZERO": {
        "hr": "{field} mora biti veći ili jednak nuli.",
        "en": "{field} must be greater than or equal to zero.",
        "de": "{field} muss größer oder gleich null sein.",
        "hu": "A(z) {field} értéknek nullánál nagyobbnak vagy egyenlőnek kell lennie.",
    },
    "FIELD_NOT_DATE": {
        "hr": "{field} mora biti valjani ISO datum.",
        "en": "{field} must be a valid ISO date.",
        "de": "{field} muss ein gültiges ISO-Datum sein.",
        "hu": "A(z) {field} érvényes ISO-dátumnak kell lennie.",
    },
    "FIELD_BOOL_TRUE_FALSE": {
        "hr": "{field} mora biti 'true' ili 'false'.",
        "en": "{field} must be 'true' or 'false'.",
        "de": "{field} muss 'true' oder 'false' sein.",
        "hu": "A(z) {field} értéke 'true' vagy 'false' kell legyen.",
    },
    "FIELD_ONE_OF": {
        "hr": "{field} mora biti jedno od: {options}.",
        "en": "{field} must be one of: {options}.",
        "de": "{field} muss eines von folgenden sein: {options}.",
        "hu": "A(z) {field} értékének ezek egyikének kell lennie: {options}.",
    },
    "QUERY_PARAM_REQUIRED": {
        "hr": "Query parametar '{field}' je obavezan.",
        "en": "Query parameter '{field}' is required.",
        "de": "Der Query-Parameter '{field}' ist erforderlich.",
        "hu": "A '{field}' query paraméter megadása kötelező.",
    },
    "SETUP_LOCATION_NAME_REQUIRED": {
        "hr": "Naziv lokacije je obavezan.",
        "en": "Location name is required.",
        "de": "Standortname ist erforderlich.",
        "hu": "A helyszín neve kötelező.",
    },
    "SETUP_LOCATION_NAME_TOO_LONG": {
        "hr": "Naziv lokacije mora imati najviše {max_length} znakova.",
        "en": "Location name must be {max_length} characters or fewer.",
        "de": "Standortname darf höchstens {max_length} Zeichen lang sein.",
        "hu": "A helyszín neve legfeljebb {max_length} karakter lehet.",
    },
    "RECEIVING_NO_LINES": {
        "hr": "Barem jedna stavka mora biti primljena.",
        "en": "At least one line must be received.",
        "de": "Mindestens eine Position muss empfangen werden.",
        "hu": "Legalább egy sort be kell fogadni.",
    },
    "RECEIVING_ADHOC_NOTE_REQUIRED": {
        "hr": "Za ad-hoc primitke obavezna je napomena.",
        "en": "A note is required for ad-hoc receipts.",
        "de": "Für Ad-hoc-Empfänge ist eine Notiz erforderlich.",
        "hu": "Ad-hoc bevételezésekhez megjegyzés szükséges.",
    },
    "ORDER_INVALID_VIEW": {
        "hr": "Parametar 'view' mora biti 'receiving' ako je naveden.",
        "en": "view must be 'receiving' when provided.",
        "de": "Der Parameter 'view' muss 'receiving' sein, wenn angegeben.",
        "hu": "A 'view' paraméternek 'receiving' értékűnek kell lennie, ha meg van adva.",
    },
    "DRAFT_BATCH_ID_REQUIRED": {
        "hr": "batch_id je obavezan za artikle s praćenjem serije.",
        "en": "batch_id is required for batch-tracked articles.",
        "de": "batch_id ist für chargenverfolgte Artikel erforderlich.",
        "hu": "A batch_id kötelező a kötegelt nyomon követésű cikkekhez.",
    },
    "ARTICLE_DUPLICATE_SUPPLIER_ID": {
        "hr": "Dobavljači sadrže duplikate supplier_id vrijednosti.",
        "en": "suppliers contains duplicate supplier_id values.",
        "de": "Lieferanten enthalten doppelte supplier_id-Werte.",
        "hu": "A szállítók ismétlődő supplier_id értékeket tartalmaznak.",
    },
    "ARTICLE_INACTIVE_SUPPLIER": {
        "hr": "Dobavljači moraju biti aktivni.",
        "en": "suppliers must reference active suppliers only.",
        "de": "Lieferanten müssen ausschließlich aktive Lieferanten referenzieren.",
        "hu": "A szállítók csak aktív szállítókra hivatkozhatnak.",
    },
    # ── Generic / structural errors ──────────────────────────────────────────
    "VALIDATION_ERROR": {
        "hr": "Greška pri provjeri valjanosti podataka.",
        "en": "Validation error.",
        "de": "Validierungsfehler.",
        "hu": "Érvényesítési hiba.",
    },
    "FORBIDDEN": {
        "hr": "Nema ovlasti za pristup ovom resursu.",
        "en": "Not permitted for this endpoint.",
        "de": "Keine Berechtigung für diesen Endpunkt.",
        "hu": "Nincs jogosultság ehhez a végponthoz.",
    },
    "BAD_REQUEST": {
        "hr": "Zahtjev nije ispravan.",
        "en": "Bad request.",
        "de": "Ungültige Anfrage.",
        "hu": "Hibás kérés.",
    },
    "CONFLICT": {
        "hr": "Konflikt pri obradi zahtjeva.",
        "en": "Conflict.",
        "de": "Konflikt.",
        "hu": "Ütközés.",
    },
    "UNAUTHORIZED": {
        "hr": "Korisnik nije pronađen ili je račun neaktivan.",
        "en": "User not found or account is inactive.",
        "de": "Benutzer nicht gefunden oder Konto ist inaktiv.",
        "hu": "A felhasználó nem található vagy a fiók inaktív.",
    },
    "INTERNAL_ERROR": {
        "hr": "Interna greška sustava.",
        "en": "Internal server error.",
        "de": "Interner Serverfehler.",
        "hu": "Belső szerverhiba.",
    },
    # ── Auth errors ───────────────────────────────────────────────────────────
    "TOKEN_EXPIRED": {
        "hr": "Token je istekao.",
        "en": "Token has expired.",
        "de": "Token ist abgelaufen.",
        "hu": "A token lejárt.",
    },
    "TOKEN_INVALID": {
        "hr": "Potpis ili format tokena nije ispravan.",
        "en": "Token signature or format is invalid.",
        "de": "Token-Signatur oder -Format ist ungültig.",
        "hu": "A token aláírása vagy formátuma érvénytelen.",
    },
    "TOKEN_MISSING": {
        "hr": "Autorizacijski token je obavezan.",
        "en": "Authorization token is required.",
        "de": "Autorisierungstoken ist erforderlich.",
        "hu": "Hitelesítési token szükséges.",
    },
    "TOKEN_REVOKED": {
        "hr": "Token je opozvan.",
        "en": "Token has been revoked.",
        "de": "Token wurde widerrufen.",
        "hu": "A token vissza lett vonva.",
    },
    "RATE_LIMITED": {
        "hr": "Previše pokušaja prijave. Molimo pričekajte trenutak.",
        "en": "Too many login attempts. Please wait a moment before trying again.",
        "de": "Zu viele Anmeldeversuche. Bitte warten Sie einen Moment.",
        "hu": "Túl sok bejelentkezési kísérlet. Kérjük, várjon egy pillanatig.",
    },
    "INVALID_CREDENTIALS": {
        "hr": "Nevažeće korisničko ime ili lozinka.",
        "en": "Invalid username or password.",
        "de": "Ungültiger Benutzername oder ungültiges Passwort.",
        "hu": "Érvénytelen felhasználónév vagy jelszó.",
    },
    "MISSING_CREDENTIALS": {
        "hr": "Korisničko ime i lozinka su obavezni.",
        "en": "username and password are required.",
        "de": "Benutzername und Passwort sind erforderlich.",
        "hu": "Felhasználónév és jelszó megadása kötelező.",
    },
    "ACCOUNT_INACTIVE": {
        "hr": "Korisnički račun je neaktivan.",
        "en": "Account is inactive.",
        "de": "Konto ist inaktiv.",
        "hu": "A fiók inaktív.",
    },
    # ── Printer errors (Phase 8 Wave 2) ──────────────────────────────────────
    "PRINTER_NOT_CONFIGURED": {
        "hr": "Pisač nije konfiguriran. Postavite IP adresu pisača u postavkama.",
        "en": "Printer is not configured. Set the printer IP address in settings.",
        "de": "Drucker ist nicht konfiguriert. Stellen Sie die Drucker-IP-Adresse in den Einstellungen ein.",
        "hu": "A nyomtató nincs konfigurálva. Állítsa be a nyomtató IP-címét a beállításokban.",
    },
    "PRINTER_UNREACHABLE": {
        "hr": "Pisač nije dostupan na adresi {printer_ip}.",
        "en": "Printer is not reachable at {printer_ip}.",
        "de": "Drucker ist nicht erreichbar unter {printer_ip}.",
        "hu": "A nyomtató nem érhető el a következő címen: {printer_ip}.",
    },
    "PRINTER_MODEL_UNKNOWN": {
        "hr": "Nepoznat model pisača: {model}.",
        "en": "Unknown printer model: {model}.",
        "de": "Unbekanntes Druckermodell: {model}.",
        "hu": "Ismeretlen nyomtatómodell: {model}.",
    },
}


# ---------------------------------------------------------------------------
# Locale resolution
# ---------------------------------------------------------------------------

_ACCEPT_LANG_RE = re.compile(r"([a-zA-Z]{2,3})(?:[_\-][a-zA-Z0-9]+)?(?:;[^,]*)?")
_VALIDATION_REQUIRED_QUERY_RE = re.compile(r"^Query parameter '([^']+)' is required\.$")
_VALIDATION_REQUIRED_RE = re.compile(r"^'?([^']+?)'? is required\.$")
_VALIDATION_TOO_LONG_RE = re.compile(r"^'?([^']+?)'? must be (\d+) characters or fewer\.$")
_VALIDATION_INT_RE = re.compile(r"^'?([^']+?)'? must be a valid integer\.$")
_VALIDATION_NUMBER_RE = re.compile(r"^'?([^']+?)'? must be a valid number\.$")
_VALIDATION_GT_ZERO_RE = re.compile(r"^'?([^']+?)'? must be greater than (?:zero|0)\.$")
_VALIDATION_GTE_ZERO_RE = re.compile(
    r"^'?([^']+?)'?\s+must be (?:greater than or equal to (?:zero|0)|>= 0)\.$"
)
_VALIDATION_DATE_RE = re.compile(r"^'?([^']+?)'? must be a valid ISO date\.$")
_VALIDATION_BOOL_RE = re.compile(r"^'?([^']+?)'? must be 'true' or 'false'\.$")
_VALIDATION_ONE_OF_RE = re.compile(r"^'?([^']+?)'? must be one of: (.+)\.$")


def _primary_tag_from_header(header: str) -> str | None:
    """Extract the first locale tag from an Accept-Language header value."""
    # Handle "hr-HR,hr;q=0.9,en;q=0.8" → "hr"
    for match in _ACCEPT_LANG_RE.finditer(header):
        tag = match.group(1).lower()
        if tag in SUPPORTED_LOCALES:
            return tag
    return None


def _settings_default_language() -> str | None:
    """Read default_language from SystemConfig if available and supported."""
    try:
        from app.models.system_config import SystemConfig  # local import to avoid circulars

        row = SystemConfig.query.filter_by(key="default_language").first()
        if row and row.value in SUPPORTED_LOCALES:
            return row.value
    except Exception:  # noqa: BLE001 — DB might not be ready in all contexts
        pass
    return None


def resolve_locale(req=None) -> str:
    """Determine the best supported locale for the current request.

    Priority:
    1. Accept-Language header primary supported tag
    2. SystemConfig.default_language (when available and supported)
    3. ``hr`` (hard-coded final fallback)
    """
    _req = req or flask_request
    try:
        accept = _req.headers.get("Accept-Language", "")
    except RuntimeError:
        # No active request context (e.g. background tasks).
        accept = ""

    if accept:
        tag = _primary_tag_from_header(accept)
        if tag:
            return tag

    default = _settings_default_language()
    if default:
        return default

    return _DEFAULT_FALLBACK


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------


def translate(key: str, locale: str, details: dict[str, Any] | None = None) -> str | None:
    """Return the translated message for *key* in *locale*, or ``None``.

    If *details* contains template placeholders (e.g. ``{batch_code}``), they
    are substituted with the corresponding values from *details*.
    Unknown placeholders are left unchanged.
    """
    locale_map = MESSAGES.get(key)
    if locale_map is None:
        return None

    template = locale_map.get(locale) or locale_map.get("en")
    if template is None:
        return None

    if details and "{" in template:
        try:
            return template.format_map({k: v for k, v in details.items() if not k.startswith("_")})
        except (KeyError, ValueError):
            return template

    return template


def _translate_validation_fallback(fallback: str, locale: str) -> str | None:
    """Translate common field-specific VALIDATION_ERROR fallback messages."""
    if not fallback:
        return None

    pattern_map = (
        (
            _VALIDATION_REQUIRED_QUERY_RE,
            "QUERY_PARAM_REQUIRED",
            lambda match: {"field": match.group(1)},
        ),
        (
            _VALIDATION_REQUIRED_RE,
            "FIELD_REQUIRED",
            lambda match: {"field": match.group(1)},
        ),
        (
            _VALIDATION_TOO_LONG_RE,
            "FIELD_TOO_LONG",
            lambda match: {"field": match.group(1), "max_length": match.group(2)},
        ),
        (
            _VALIDATION_INT_RE,
            "FIELD_NOT_INTEGER",
            lambda match: {"field": match.group(1)},
        ),
        (
            _VALIDATION_NUMBER_RE,
            "FIELD_NOT_NUMBER",
            lambda match: {"field": match.group(1)},
        ),
        (
            _VALIDATION_GT_ZERO_RE,
            "FIELD_NOT_POSITIVE",
            lambda match: {"field": match.group(1)},
        ),
        (
            _VALIDATION_GTE_ZERO_RE,
            "FIELD_GTE_ZERO",
            lambda match: {"field": match.group(1)},
        ),
        (
            _VALIDATION_DATE_RE,
            "FIELD_NOT_DATE",
            lambda match: {"field": match.group(1)},
        ),
        (
            _VALIDATION_BOOL_RE,
            "FIELD_BOOL_TRUE_FALSE",
            lambda match: {"field": match.group(1)},
        ),
        (
            _VALIDATION_ONE_OF_RE,
            "FIELD_ONE_OF",
            lambda match: {"field": match.group(1), "options": match.group(2)},
        ),
    )

    for pattern, key, detail_builder in pattern_map:
        match = pattern.match(fallback)
        if not match:
            continue
        details = detail_builder(match)
        translated = translate(key, locale, details)
        if translated is not None:
            return translated

    return None


def localize_message(
    error_code: str,
    details: dict[str, Any] | None = None,
    *,
    fallback: str = "",
    req=None,
) -> str:
    """Resolve and return a localized message for *error_code*.

    Checks ``details["_msg_key"]`` first so service helpers can select a more
    specific template for generic codes like ``VALIDATION_ERROR``.

    Falls back to *fallback* (the original English message) if no catalog
    entry is found.
    """
    locale = resolve_locale(req)
    details = details or {}
    msg_key = details.get("_msg_key")

    if msg_key:
        result = translate(msg_key, locale, details)
        if result is not None:
            return result

    if error_code == "VALIDATION_ERROR":
        inferred = _translate_validation_fallback(fallback, locale)
        if inferred is not None:
            return inferred
        if fallback:
            return fallback

    result = translate(error_code, locale, details)
    if result is not None:
        return result

    return fallback or error_code
