from __future__ import annotations
"""Google Ads API — Keyword Plan Idea Service.

Provides real monthly search volumes and competition data for any keyword list.

── Setup (one-time) ──────────────────────────────────────────────────────────
1. Create a Google Cloud project:
   https://console.cloud.google.com/

2. Enable the Google Ads API:
   APIs & Services → Library → "Google Ads API" → Enable

3. Create OAuth2 Desktop credentials:
   APIs & Services → Credentials → Create Credentials → OAuth client ID → Desktop app
   Download the JSON → note client_id and client_secret

4. Apply for a Google Ads developer token (free, takes 1-2 days):
   https://developers.google.com/google-ads/api/docs/first-call/dev-token
   You need a Google Ads manager account (MCC) — free to create.

5. Run the OAuth2 flow to get a refresh token:
   pip install google-auth-oauthlib
   python -c "
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json',
       scopes=['https://www.googleapis.com/auth/adwords'])
   creds = flow.run_local_server(port=0)
   print('refresh_token:', creds.refresh_token)
   "

6. Add to your .env file:
   GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
   GOOGLE_ADS_CLIENT_ID=your_client_id.apps.googleusercontent.com
   GOOGLE_ADS_CLIENT_SECRET=your_client_secret
   GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
   GOOGLE_ADS_CUSTOMER_ID=1234567890   # 10-digit, no dashes

7. Install the library:
   pip install google-ads
──────────────────────────────────────────────────────────────────────────────
"""
import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = [
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN",
    "GOOGLE_ADS_CUSTOMER_ID",
]

# Spain geo target constant
_GEO_SPAIN = "geoTargetConstants/2724"

# Spanish language constant
_LANG_SPANISH = "languageConstants/1003"

_COMPETITION_LABELS = {
    "UNKNOWN":  "—",
    "LOW":      "🟢 Baja",
    "MEDIUM":   "🟡 Media",
    "HIGH":     "🔴 Alta",
}


@dataclass
class KeywordIdea:
    keyword:              str
    avg_monthly_searches: int
    competition:          str   # raw: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"
    competition_index:    int   # 0–100
    competition_label:    str   # human-readable

    @property
    def searches_display(self) -> str:
        if self.avg_monthly_searches >= 1_000_000:
            return f"{self.avg_monthly_searches / 1_000_000:.1f}M"
        if self.avg_monthly_searches >= 1_000:
            return f"{self.avg_monthly_searches / 1_000:.0f}K"
        return str(self.avg_monthly_searches)


def credentials_available() -> bool:
    """Return True if all required Google Ads env vars are set."""
    return all(os.getenv(k) for k in _REQUIRED_ENV_VARS)


def missing_credentials() -> list[str]:
    """Return list of env var names that are not set."""
    return [k for k in _REQUIRED_ENV_VARS if not os.getenv(k)]


def generate_keyword_ideas(
    seed_keywords: list[str],
    limit: int = 50,
) -> tuple[list[KeywordIdea], str | None]:
    """Fetch keyword ideas + monthly search volumes from Google Ads API.

    Returns:
        (ideas, error_message) — error_message is None on success.
    """
    if not credentials_available():
        missing = missing_credentials()
        return [], f"Credenciales no configuradas: {', '.join(missing)}"

    try:
        from google.ads.googleads.client import GoogleAdsClient  # type: ignore
    except ImportError:
        return [], (
            "Librería 'google-ads' no instalada. "
            "Ejecuta: pip install google-ads"
        )

    try:
        client = GoogleAdsClient.load_from_dict({
            "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
            "client_id":       os.environ["GOOGLE_ADS_CLIENT_ID"],
            "client_secret":   os.environ["GOOGLE_ADS_CLIENT_SECRET"],
            "refresh_token":   os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
            "login_customer_id": os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", ""),
            "use_proto_plus":  True,
        })

        kp_service = client.get_service("KeywordPlanIdeaService")
        request    = client.get_type("GenerateKeywordIdeasRequest")

        customer_id = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
        request.customer_id = customer_id
        request.language = _LANG_SPANISH
        request.geo_target_constants.append(_GEO_SPAIN)
        request.include_adult_keywords = False
        request.keyword_seed.keywords.extend(seed_keywords)

        response = kp_service.generate_keyword_ideas(request=request)

        ideas: list[KeywordIdea] = []
        for idea in response:
            m = idea.keyword_idea_metrics
            comp_raw   = m.competition.name if m.competition else "UNKNOWN"
            ideas.append(KeywordIdea(
                keyword=idea.text,
                avg_monthly_searches=int(m.avg_monthly_searches or 0),
                competition=comp_raw,
                competition_index=int(m.competition_index or 0),
                competition_label=_COMPETITION_LABELS.get(comp_raw, "—"),
            ))

        ideas.sort(key=lambda x: x.avg_monthly_searches, reverse=True)
        return ideas[:limit], None

    except Exception as e:
        logger.error(f"Google Ads Keyword Planner error: {e}")
        return [], f"Error al consultar Google Ads API: {e}"


# ── Default seed keywords per TechPulse category ──────────────────────────────

SEED_KEYWORDS_BY_CATEGORY: dict[str, list[str]] = {
    "📱 Móviles": [
        "mejor móvil 2026", "smartphone android", "iphone 17",
        "samsung galaxy s25", "móvil barato", "cambiar de móvil",
    ],
    "⌚ Smartwatches": [
        "mejor smartwatch 2026", "reloj inteligente", "apple watch",
        "samsung galaxy watch", "smartwatch barato", "reloj deportivo gps",
    ],
    "📲 Tablets": [
        "mejor tablet 2026", "ipad pro", "tablet android",
        "samsung galaxy tab", "tablet para niños", "tablet para estudiar",
    ],
    "💻 Portátiles": [
        "mejor portátil 2026", "portátil gaming", "macbook air",
        "portátil barato estudiante", "copilot plus pc", "ultrabook",
    ],
    "🎮 Gaming": [
        "mejor pc gaming 2026", "tarjeta gráfica 2026", "nintendo switch 2",
        "rtx 5070", "monitor gaming", "pc gaming barato",
    ],
}
