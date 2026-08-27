"""
Weather-aware disease risk alerts for Kano State.
Uses simple rule-based correlation between weather conditions and disease risk.
"""
from datetime import date, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


# Kano State seasonal weather patterns (approximate)
SEASON_DATA = {
    "dry_hot": {"months": [2, 3, 4], "temp_range": (30, 42), "humidity": (15, 35)},
    "rainy": {"months": [5, 6, 7, 8, 9], "temp_range": (22, 35), "humidity": (60, 90)},
    "cool_dry": {"months": [10, 11, 12, 1], "temp_range": (18, 32), "humidity": (20, 50)},
}

# Disease risk rules based on season/weather
DISEASE_RISKS = {
    "Poultry (Chicken)": [
        {
            "disease": "Avian Influenza (Bird Flu)",
            "seasons": ["cool_dry"],
            "risk_level": "high",
            "description": "Cool dry weather favors AI virus survival. Monitor for sudden flock deaths.",
            "prevention": "Vaccinate, restrict farm visits, report sudden deaths immediately.",
        },
        {
            "disease": "Newcastle Disease",
            "seasons": ["rainy", "cool_dry"],
            "risk_level": "high",
            "description": "Stress from weather changes increases susceptibility.",
            "prevention": "Maintain vaccination schedule, improve ventilation.",
        },
        {
            "disease": "Coccidiosis",
            "seasons": ["rainy"],
            "risk_level": "high",
            "description": "Wet litter from humidity promotes coccidia oocyst survival.",
            "prevention": "Keep litter dry, use anticoccidial feed additives.",
        },
        {
            "disease": "Marek's Disease",
            "seasons": ["dry_hot", "cool_dry"],
            "risk_level": "moderate",
            "description": "Dust and stress from dry conditions can trigger outbreaks.",
            "prevention": "Vaccinate day-old chicks, reduce dust exposure.",
        },
    ],
    "Cattle": [
        {
            "disease": "Trypanosomiasis (Tsetse Fly)",
            "seasons": ["rainy"],
            "risk_level": "high",
            "description": "Rainy season increases tsetse fly population near riverine areas.",
            "prevention": "Use trypanocidal drugs, avoid grazing near tsetse habitats.",
        },
        {
            "disease": "Anthrax",
            "seasons": ["rainy", "cool_dry"],
            "risk_level": "moderate",
            "description": "Flooding can expose anthrax spores in soil.",
            "prevention": "Annual vaccination, avoid grazing flooded areas.",
        },
        {
            "disease": "Hemorrhagic Septicemia (HS)",
            "seasons": ["rainy"],
            "risk_level": "high",
            "description": "High humidity and temperature stress predispose to HS.",
            "prevention": "Vaccinate before rainy season, quarantine new animals.",
        },
        {
            "disease": "Foot and Mouth Disease (FMD)",
            "seasons": ["rainy", "cool_dry"],
            "risk_level": "high",
            "description": "Wet conditions favor virus survival on fomites.",
            "prevention": "Vaccinate every 6 months, restrict movement of infected animals.",
        },
    ],
    "Goat": [
        {
            "disease": "Peste des Petits Ruminants (PPR)",
            "seasons": ["cool_dry", "rainy"],
            "risk_level": "high",
            "description": "Cold stress and crowding increase PPR transmission.",
            "prevention": "Vaccinate annually, isolate sick animals.",
        },
        {
            "disease": "Dermatophytosis (Ringworm)",
            "seasons": ["rainy"],
            "risk_level": "moderate",
            "description": "Humid conditions favor fungal growth.",
            "prevention": "Keep housing dry, treat early with antifungals.",
        },
    ],
    "Sheep": [
        {
            "disease": "Sheep Pox",
            "seasons": ["cool_dry"],
            "risk_level": "moderate",
            "description": "Cold weather stress triggers latent infections.",
            "prevention": "Vaccinate, quarantine new stock.",
        },
    ],
}

# LGAs with specific risk factors
HIGH_RISK_LGAS = {
    "Tudun Wada": ["tsetse_corridor"],
    "Doguwa": ["tsetse_corridor"],
    "Sumaila": ["tsetse_corridor"],
    "Rano": ["flooding_risk"],
            "Bunkure": ["flooding_risk"],
}


def get_current_season():
    month = date.today().month
    for season_name, data in SEASON_DATA.items():
        if month in data["months"]:
            return season_name
    return "dry_hot"


def get_risk_level_color(level):
    return {"high": "red", "moderate": "amber", "low": "green"}.get(level, "gray")


class WeatherDiseaseRiskView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lga = request.query_params.get('lga', '').strip()
        species = request.query_params.get('species', '').strip()

        season = get_current_season()
        season_info = SEASON_DATA[season]
        today = date.today()

        # Get risks for requested species (or all)
        risks = []
        species_list = [species] if species else DISEASE_RISKS.keys()

        for sp in species_list:
            for risk in DISEASE_RISKS.get(sp, []):
                if season in risk["seasons"]:
                    risk_entry = {
                        "species": sp,
                        "disease": risk["disease"],
                        "riskLevel": risk["risk_level"],
                        "color": get_risk_level_color(risk["risk_level"]),
                        "description": risk["description"],
                        "prevention": risk["prevention"],
                        "season": season.replace("_", " ").title(),
                    }
                    if lga:
                        lga_risks = HIGH_RISK_LGAS.get(lga, [])
                        if any("tsetse" in r for r in lga_risks) and "trypanosomiasis" in risk["disease"].lower():
                            risk_entry["localFactor"] = "This LGA is in a tsetse fly corridor — extra caution needed."
                        if any("flood" in r for r in lga_risks) and "anthrax" in risk["disease"].lower():
                            risk_entry["localFactor"] = "This LGA has flooding risk — avoid grazing low-lying areas."
                    risks.append(risk_entry)

        # Sort by risk level
        level_order = {"high": 0, "moderate": 1, "low": 2}
        risks.sort(key=lambda x: level_order.get(x["riskLevel"], 3))

        # Available LGAs
        all_lgas = sorted(list(HIGH_RISK_LGAS.keys()) + [
            "Kano Municipal", "Nassarawa", "Ungogo", "Kumbotso", "Gwale",
            "Dala", "Fagge", "Tarauni", "KMETO", "Gezawa",
            "Bichi", "Gwarzo", "Karaye", "Rogo", "Kiru",
            "Bebeji", "Gabasawa", "Minjibir", "Dawakin Tofa", "Tofa",
        ])

        return Response({
            "season": season.replace("_", " ").title(),
            "temperature": f"{season_info['temp_range'][0]}–{season_info['temp_range'][1]}°C",
            "humidity": f"{season_info['humidity'][0]}–{season_info['humidity'][1]}%",
            "risks": risks,
            "totalRisks": len(risks),
            "highRisks": len([r for r in risks if r["riskLevel"] == "high"]),
            "availableLgas": all_lgas,
        })
