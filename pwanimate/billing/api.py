"""
Billing & usage API.

- GET /api/pwanimate/billing/quota/  compact payload for the composer chip
  (the quota spinner) — cheap enough to poll.
- GET /api/pwanimate/billing/usage/  the full snapshot for the hover modal
  and the settings dashboard.

Both read the same counters the quota check enforces, so the number the
student sees is the number we act on.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import QuotaService, TierService


class PwanimateBillingQuotaView(APIView):
    """Compact: what the composer chip needs on every render."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        snapshot = QuotaService.snapshot(request.user, days=1)
        windows = snapshot.get("windows", {})
        day = windows.get("day", {})
        chats = day.get("chats", {}) or {}
        images = day.get("images", {}) or {}
        tokens = day.get("tokens", {}) or {}
        return Response(
            {
                "quota": {
                    "tier": snapshot.get("tier"),
                    "state": snapshot.get("state"),
                    "chats": {
                        "used": chats.get("used", 0),
                        "limit": chats.get("limit"),
                        "remaining": chats.get("remaining"),
                    },
                    "images": {
                        "used": images.get("used", 0),
                        "limit": images.get("limit"),
                        "remaining": images.get("remaining"),
                    },
                    "tokens": {
                        "prompt": tokens.get("prompt", 0),
                        "completion": tokens.get("completion", 0),
                        "total": tokens.get("total", 0),
                    },
                    "resets_at": snapshot.get("resets_at", {}).get("day"),
                }
            },
            status=status.HTTP_200_OK,
        )


class PwanimateBillingUsageView(APIView):
    """Full: the hover modal and the settings → Usage dashboard."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        snapshot = QuotaService.snapshot(request.user)
        return Response({"usage": snapshot}, status=status.HTTP_200_OK)


class PwanimateBillingTiersView(APIView):
    """The tier catalogue + the caller's entitlements (the UI renders from this)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import CostClass, ModelOffering, Tier

        tiers = []
        for tier in Tier.objects.filter(is_active=True).order_by("rank"):
            tiers.append(
                {
                    "code": tier.code,
                    "name": tier.name,
                    "rank": tier.rank,
                    "price_kes": float(tier.price_kes),
                    "duration_days": tier.duration_days,
                    "description": tier.description,
                    "entitlements": tier.entitlements or {},
                }
            )
        current = TierService.resolve_tier(request.user)
        current_rank = current.rank if current else 0

        # The premium capability (frontier/paid class) the caller's tier may
        # use, with the allowance it has left today. The UI renders a chip
        # from this — it never hardcodes a model name.
        premium = []
        for offering in ModelOffering.objects.filter(
            is_active=True, cost_class__in=[CostClass.FRONTIER, CostClass.PAID_FLASH]
        ).select_related("min_tier"):
            allowed = offering.min_tier is None or offering.min_tier.rank <= current_rank
            decision = QuotaService.check(request.user, kind="premium_turn")
            premium.append(
                {
                    "key": offering.key,
                    "label": offering.display_name or offering.model_id,
                    "capability": "frontier" if offering.cost_class == CostClass.FRONTIER else "premium",
                    "allowed": allowed,
                    "required_tier": offering.min_tier.code if offering.min_tier else None,
                    "remaining_today": decision.remaining.get("day"),
                    "state": decision.state,
                }
            )
        return Response(
            {
                "tiers": tiers,
                "current_tier": current.code if current else None,
                "premium": premium,
            },
            status=status.HTTP_200_OK,
        )
