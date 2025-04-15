import http.client
import ollama
import json
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timedelta
import time
import requests


TRENDING_PLACES = {
    "Asia": [
        {"name": "Osaka, Japan", "popularity": 25000, "skyscanner_code": "OSAA", "hotel_market": "Osaka, JP"},
        {"name": "Bali, Indonesia", "popularity": 22000, "skyscanner_code": "DPSA", "hotel_market": "Bali, ID"},
        {"name": "Kuala Lumpur, Malaysia", "popularity": 18000, "skyscanner_code": "KUL", "hotel_market": "Kuala Lumpur, MY"},
    ],
    "Europe": [
        {"name": "Santorini, Greece", "popularity": 24500, "skyscanner_code": "JTRA", "hotel_market": "Santorini, GR"},
        {"name": "Amalfi Coast, Italy", "popularity": 16500, "skyscanner_code": "NAP", "hotel_market": "Naples, IT"},
        {"name": "Lisbon, Portugal", "popularity": 14000, "skyscanner_code": "LIS", "hotel_market": "Lisbon, PT"},
    ],
    "North America": [
        {"name": "New York City, NY, USA", "popularity": 20000, "skyscanner_code": "NYCA", "hotel_market": "New York, US"},
        {"name": "Tulum, Mexico", "popularity": 17000, "skyscanner_code": "CUN", "hotel_market": "Tulum, MX"},
        {"name": "Banff, Canada", "popularity": 15000, "skyscanner_code": "YYC", "hotel_market": "Banff, CA"},
    ],
    "Africa": [
        {"name": "Cape Town, South Africa", "popularity": 19000, "skyscanner_code": "CPT", "hotel_market": "Cape Town, ZA"},
        {"name": "Marrakech, Morocco", "popularity": 17500, "skyscanner_code": "RAK", "hotel_market": "Marrakech, MA"},
    ],
    "South America": [
        {"name": "Machu Picchu, Peru", "popularity": 18500, "skyscanner_code": "CUZ", "hotel_market": "Cusco, PE"},
        {"name": "Rio de Janeiro, Brazil", "popularity": 17000, "skyscanner_code": "GIG", "hotel_market": "Rio de Janeiro, BR"},
    ],
    "Australia": [
        {"name": "Sydney, Australia", "popularity": 20000, "skyscanner_code": "SYD", "hotel_market": "Sydney, AU"},
        {"name": "Great Barrier Reef, Australia", "popularity": 18000, "skyscanner_code": "CNS", "hotel_market": "Cairns, AU"},
    ],
}

# Mock food costs
FOOD_ESTIMATES = {
    "Osaka, Japan": 50,
    "Bali, Indonesia": 30,
    "Kuala Lumpur, Malaysia": 25,
    "Santorini, Greece": 60,
    "Amalfi Coast, Italy": 70,
    "Lisbon, Portugal": 40,
    "New York City, NY, USA": 80,
    "Tulum, Mexico": 50,
    "Banff, Canada": 60,
    "Cape Town, South Africa": 45,
    "Marrakech, Morocco": 35,
    "Machu Picchu, Peru": 40,
    "Rio de Janeiro, Brazil": 50,
    "Sydney, Australia": 60,
    "Great Barrier Reef, Australia": 55,
}

def fetch_trending_places(region):
    """Fetch trending places using SerpAPI."""
    url = "https://serpapi.com/search"
    params = {
        "q": f"trending travel destinations 2025 {region}",
        "api_key": "SerpAPI key",
        "engine": "google",
        "num": 10
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        destinations = []
        for result in data.get("organic_results", []):
            title = result.get("title", "").lower()
            for place in TRENDING_PLACES.get(region, []):
                if place["name"].lower() in title:
                    destinations.append(place)
        return destinations if destinations else TRENDING_PLACES.get(region, [])
    except Exception as e:
        print(f"Error fetching trends for {region}: {e}")
        return TRENDING_PLACES.get(region, [])

def fetch_flight_price(origin, destination, origin_code, dest_code):
    """Fetch flight price using Skyscanner API."""
    conn = http.client.HTTPSConnection("skyscanner89.p.rapidapi.com")
    headers = {
        'x-rapidapi-host': "skyscanner89.p.rapidapi.com",
        'x-rapidapi-key': "key"
    }
    endpoint = f"/flights/one-way/list?origin={origin_code}&originId=27537542&destination={dest_code}&destinationId=95673827"
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        json_data = json.loads(data)
        price = json_data.get("content", {}).get("results", {}).get("quotes", [{}])[0].get("price", {}).get("amount", 0)
        return float(price) if price else 0
    except Exception as e:
        print(f"Error fetching flight for {destination}: {e}")
        return 0
    finally:
        conn.close()

def fetch_hotel_price(destination, nights=5):
    """Fetch hotel price using Skyscanner API."""
    conn = http.client.HTTPSConnection("skyscanner89.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': "key",
        'x-rapidapi-host': "skyscanner89.p.rapidapi.com"
    }
    checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=30 + nights)).strftime("%Y-%m-%d")
    market = next((p["hotel_market"] for p in sum(TRENDING_PLACES.values(), []) if p["name"] == destination), "")
    endpoint = f"/hotels/price?market={market}&locale=en-US&checkin_date={checkin}&checkout_date={checkout}¤cy=USD&adults=2"
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        json_data = json.loads(data)
        hotels = json_data.get("results", {}).get("hotels", [])
        if hotels:
            prices = [float(h.get("price", 0)) for h in hotels if h.get("price")]
            return sum(prices) / len(prices) / nights if prices else 0
        return 0
    except Exception as e:
        print(f"Error fetching hotel for {destination}: {e}")
        return 0
    finally:
        conn.close()

def fetch_expenses(destination, origin="NYCA", origin_name="New York", nights=5):
    """Fetch expenses with Skyscanner APIs."""
    dest_code = next((p["skyscanner_code"] for p in sum(TRENDING_PLACES.values(), []) if p["name"] == destination), "")
    if not dest_code:
        return None

    flight_price = fetch_flight_price(origin_name, destination, origin, dest_code)
    hotel_price = fetch_hotel_price(destination, nights)
    food_price = FOOD_ESTIMATES.get(destination, 50)

    total = (hotel_price * nights) + flight_price + (food_price * nights)
    return {
        "hotel_per_night": hotel_price,
        "flight": flight_price,
        "daily_food": food_price,
        "total": total,
        "nights": nights
    }

def fetch_reviews(destination):
    """Mock reviews."""
    reviews = {
        "Osaka, Japan": ["Vibrant culture!", "Busy streets."],
        "Bali, Indonesia": ["Gorgeous beaches!", "Some crowded spots."],
        "Santorini, Greece": ["Stunning views!", "Pricey dining."],
        "Cape Town, South Africa": ["Beautiful landscapes!", "Vibrant city."],
        "Marrakech, Morocco": ["Exotic markets!", "Hot weather."],
        "Machu Picchu, Peru": ["Incredible ruins!", "Challenging trek."],
        "Rio de Janeiro, Brazil": ["Lively beaches!", "Crowded festivals."],
        "Sydney, Australia": ["Iconic landmarks!", "Pricey stays."],
        "Great Barrier Reef, Australia": ["Stunning marine life!", "Remote access."],
    }
    return reviews.get(destination, ["No reviews available."])

def generate_recommendation(region, preferences, budget, nights=5, trending_places=None):
    """Generate recommendation using LLM."""
    places = trending_places or TRENDING_PLACES.get(region, [])
    if not places:
        return f"No trending places found for {region}. Please try another region."

    prompt = f"""
    You are a travel expert. Recommend the best destination in {region} based on preferences and budget. Provide a brief reason, estimated cost, and review summary.

    Trending places: {', '.join([p['name'] for p in places])}.
    Preferences: {preferences}.
    Budget: ${budget} for {nights} nights.
    Format:
    **Destination**: <place>
    **Why**: <reason>
    **Estimated Cost**: <total cost>
    **Reviews**: <summary>
    """
    try:
        response = ollama.generate(model="llama3:latest", prompt=prompt)["response"]
        return response
    except Exception as e:
        print(f"LLM error: {e}")
        return f"Error generating recommendation for {region}."

def save_to_pdf(recommendations, filename="travel_recommendations.pdf"):
    """Save to PDF."""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    for rec in recommendations:
        story.append(Paragraph(rec, styles["Normal"]))
        story.append(Spacer(1, 12))
    doc.build(story)
    print(f"Saved to {filename}")

def main():
    # User inputs
    supported_regions = list(TRENDING_PLACES.keys())
    print(f"Supported regions: {', '.join(supported_regions)}")
    region = input("Enter region (e.g., Asia, Europe): ").strip().title()
    if region not in supported_regions:
        print(f"Region '{region}' not in supported list, but attempting to fetch trends...")

    preferences = input("Enter preferences (e.g., culture, adventure): ") or "culture, relaxation"
    budget = int(input("Enter budget ($): ") or 2000)
    nights = int(input("Enter nights: ") or 5)
    origin = input("Enter origin airport code (e.g., NYCA): ") or "NYCA"
    origin_name = input("Enter origin city (e.g., New York): ") or "New York"

    recommendations = []
    # Fetch trending places
    trending_places = fetch_trending_places(region)
    if not trending_places:
        print(f"No trends found for {region}. Using fallback data.")

    # Generate recommendation
    rec = generate_recommendation(region, preferences, budget, nights, trending_places)
    print(f"Generated recommendation: {rec}")  # Debug output
    if "**Destination**:" in rec:
        dest = rec.split("**Destination**: ")[1].split("\n")[0]
        expenses = fetch_expenses(dest, origin, origin_name, nights)
        reviews = fetch_reviews(dest)
        if expenses:
            rec += f"\n**Detailed Expenses**: Hotel ${expenses['hotel_per_night']:.2f}/night, Flight ${expenses['flight']:.2f}, Food ${expenses['daily_food']:.2f}/day, Total ${expenses['total']:.2f}"
        rec += f"\n**Review Summary**: {', '.join(reviews)}"
    else:
        print(f"Skipping expenses/reviews due to invalid recommendation format")

    recommendations.append(rec)
    print(rec)
    print("-" * 50)
    save_to_pdf(recommendations)

if __name__ == "__main__":
    main()