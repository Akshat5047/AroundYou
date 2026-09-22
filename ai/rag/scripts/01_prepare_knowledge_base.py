import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT = BASE_DIR / "data" / "destination_knowledge.csv"

destinations = [
    {
        "spot_name": "Charminar",
        "district": "Hyderabad",
        "category": "Historical Monument",
        "knowledge_type": "destination",
        "content": (
            "Charminar is a historic monument in Hyderabad, Telangana. "
            "It is one of the city's major heritage landmarks and is located "
            "in the historic old-city area near Laad Bazaar and Mecca Masjid."
        )
    },
    {
        "spot_name": "Golconda Fort",
        "district": "Hyderabad",
        "category": "Fort",
        "knowledge_type": "destination",
        "content": (
            "Golconda Fort is a historic fortified complex in Hyderabad, "
            "Telangana. The site is known for its fortifications, elevated "
            "views and acoustic features. Exploring the complex involves "
            "considerable walking and climbing."
        )
    },
    {
        "spot_name": "Salar Jung Museum",
        "district": "Hyderabad",
        "category": "Museum",
        "knowledge_type": "destination",
        "content": (
            "Salar Jung Museum is a major museum in Hyderabad containing "
            "collections of art, sculptures, manuscripts, textiles, clocks, "
            "furniture and other historical objects from India and abroad."
        )
    },
    {
        "spot_name": "Ramappa Temple",
        "district": "Mulugu",
        "category": "Temple",
        "knowledge_type": "destination",
        "content": (
            "Ramappa Temple, also known as Rudreshwara Temple, is a historic "
            "Kakatiya-era temple in Telangana. It is known for its architecture "
            "and detailed sculptural work."
        )
    },
    {
        "spot_name": "Thousand Pillar Temple",
        "district": "Hanamkonda",
        "category": "Temple",
        "knowledge_type": "destination",
        "content": (
            "Thousand Pillar Temple is a historic Kakatiya-era temple complex "
            "in Hanamkonda, Telangana. It is known for its stone architecture "
            "and sculptural craftsmanship."
        )
    },
    {
        "spot_name": "Warangal Fort",
        "district": "Warangal",
        "category": "Fort",
        "knowledge_type": "destination",
        "content": (
            "Warangal Fort is a historic site associated with the Kakatiya "
            "dynasty in Telangana. The site contains monumental stone gateways, "
            "ruins and architectural remains."
        )
    },
    {
        "spot_name": "Bhongir Fort",
        "district": "Yadadri Bhuvanagiri",
        "category": "Fort",
        "knowledge_type": "destination",
        "content": (
            "Bhongir Fort is a hill fort at Bhongir in Telangana. "
            "The fort stands on a large monolithic rock formation and reaching "
            "the upper areas requires an uphill climb."
        )
    },
    {
        "spot_name": "Yadadri Temple",
        "district": "Yadadri Bhuvanagiri",
        "category": "Temple",
        "knowledge_type": "destination",
        "content": (
            "Yadadri is a major Hindu pilgrimage destination in Telangana. "
            "The temple complex is located at Yadagirigutta in Yadadri "
            "Bhuvanagiri district."
        )
    },
    {
        "spot_name": "Kuntala Waterfall",
        "district": "Nirmal",
        "category": "Waterfall",
        "knowledge_type": "destination",
        "content": (
            "Kuntala Waterfall is a natural waterfall attraction in northern "
            "Telangana. Visitor experience and water flow can vary substantially "
            "with seasonal and rainfall conditions."
        )
    },
    {
        "spot_name": "Hussain Sagar",
        "district": "Hyderabad",
        "category": "Lake",
        "knowledge_type": "destination",
        "content": (
            "Hussain Sagar is a large historic lake between Hyderabad and "
            "Secunderabad. The lake and its surrounding areas are major urban "
            "recreation and sightseeing locations."
        )
    }
]

df = pd.DataFrame(destinations)

df.insert(
    0,
    "document_id",
    [f"destination_{i:03d}" for i in range(1, len(df) + 1)]
)

df.to_csv(OUTPUT, index=False)

print("=" * 50)
print("RAG KNOWLEDGE BASE")
print("=" * 50)
print(df.to_string(index=False))
print()
print(f"Documents: {len(df)}")
print(f"Saved to: {OUTPUT}")