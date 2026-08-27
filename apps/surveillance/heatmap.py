"""
Public real-time outbreak heatmap data endpoint.
Provides LGA-level aggregation of disease reports for map visualization.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.surveillance.models import DiseaseReport


# Kano State LGA approximate coordinates for map centering
KANO_LGA_COORDS = {
    "Kano Municipal": {"lat": 12.0022, "lng": 8.5920, "population": 3626000},
    "Nassarawa": {"lat": 12.0000, "lng": 8.5700, "population": 594000},
    "Ungogo": {"lat": 12.0500, "lng": 8.5500, "population": 357000},
    "Kumbotso": {"lat": 11.9200, "lng": 8.5200, "population": 342000},
    "Gwale": {"lat": 12.0100, "lng": 8.5300, "population": 318000},
    "Dala": {"lat": 11.9800, "lng": 8.5600, "population": 415000},
    "Fagge": {"lat": 12.0100, "lng": 8.5800, "population": 241000},
    "Tarauni": {"lat": 11.9500, "lng": 8.5200, "population": 268000},
    "Tudun Wada": {"lat": 11.6500, "lng": 8.5500, "population": 292000},
    "Doguwa": {"lat": 11.3500, "lng": 8.5500, "population": 182000},
    "Sumaila": {"lat": 11.4500, "lng": 8.7000, "population": 241000},
    "Rano": {"lat": 11.5500, "lng": 8.5800, "population": 275000},
    "Bichi": {"lat": 12.2300, "lng": 8.4500, "population": 327000},
    "Gwarzo": {"lat": 12.1800, "lng": 8.3800, "population": 289000},
    "Karaye": {"lat": 12.1000, "lng": 8.2800, "population": 184000},
    "Rogo": {"lat": 12.0000, "lng": 8.2500, "population": 219000},
    "Kiru": {"lat": 11.8500, "lng": 8.2000, "population": 199000},
    "Bebeji": {"lat": 11.7500, "lng": 8.4000, "population": 167000},
    "Gabasawa": {"lat": 12.1500, "lng": 8.6000, "population": 199000},
    "Minjibir": {"lat": 12.2000, "lng": 8.6500, "population": 185000},
    "Dawakin Tofa": {"lat": 12.2500, "lng": 8.5000, "population": 253000},
    "Tofa": {"lat": 12.1800, "lng": 8.5200, "population": 145000},
    "Bunkure": {"lat": 11.7000, "lng": 8.5000, "population": 167000},
    "Kibiya": {"lat": 11.7500, "lng": 8.6000, "population": 142000},
    "Makoda": {"lat": 12.1000, "lng": 8.7000, "population": 182000},
    "Gezawa": {"lat": 12.1200, "lng": 8.6800, "population": 238000},
    "Bagwai": {"lat": 12.1500, "lng": 8.3500, "population": 166000},
    "Shanono": {"lat": 12.1000, "lng": 8.3000, "population": 143000},
    "Tsanyawa": {"lat": 12.0000, "lng": 8.3000, "population": 126000},
    "Albasu": {"lat": 11.9000, "lng": 8.3000, "population": 138000},
    "Wudil": {"lat": 11.8500, "lng": 8.7500, "population": 181000},
    "Ajingi": {"lat": 11.9500, "lng": 8.8000, "population": 131000},
    "Gaya": {"lat": 11.8500, "lng": 8.8500, "population": 156000},
}


class OutbreakHeatmapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)

        # Aggregate reports by LGA
        lga_data = (
            DiseaseReport.objects
            .filter(submitted_at__gte=since)
            .values('lga')
            .annotate(
                total_reports=Count('id'),
                suspected=Count('id', filter=Q(alert_status='Suspected')),
                confirmed=Count('id', filter=Q(alert_status='Confirmed')),
                under_investigation=Count('id', filter=Q(alert_status='Under investigation')),
                total_affected=Sum('affected'),
                total_dead=Sum('dead'),
            )
            .order_by('-total_reports')
        )

        heatmap_points = []
        for entry in lga_data:
            lga_name = entry['lga']
            coords = KANO_LGA_COORDS.get(lga_name, {})
            if not coords:
                continue

            # Risk score: higher = more urgent
            risk_score = (
                entry['confirmed'] * 10 +
                entry['under_investigation'] * 5 +
                entry['suspected'] * 2
            )

            heatmap_points.append({
                "lga": lga_name,
                "lat": coords["lat"],
                "lng": coords["lng"],
                "population": coords.get("population", 0),
                "reports": entry['total_reports'],
                "suspected": entry['suspected'],
                "confirmed": entry['confirmed'],
                "underInvestigation": entry['under_investigation'],
                "affected": entry['total_affected'] or 0,
                "dead": entry['total_dead'] or 0,
                "riskScore": risk_score,
            })

        # Top outbreaks
        top_outbreaks = sorted(heatmap_points, key=lambda x: x['riskScore'], reverse=True)[:5]

        # State-wide summary
        total_reports = DiseaseReport.objects.filter(submitted_at__gte=since).count()
        total_affected = DiseaseReport.objects.filter(
            submitted_at__gte=since
        ).aggregate(total=models_sum('affected'))['total'] or 0
        active_lgas = len(heatmap_points)

        return Response({
            "points": heatmap_points,
            "topOutbreaks": top_outbreaks,
            "summary": {
                "periodDays": days,
                "totalReports": total_reports,
                "totalAffected": total_affected,
                "activeLgas": active_lgas,
                "totalLgas": 44,
            },
        })
