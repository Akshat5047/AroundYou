from pathlib import Path
import sqlite3

from fastapi import APIRouter, HTTPException, Query


router = APIRouter(
    prefix="/api/destinations",
    tags=["Destinations"]
)


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "data"
    / "smart_tourism.db"
)


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("")
def get_destinations(
    district: str | None = Query(
        default=None,
        description="Optional Telangana district filter"
    )
):
    """
    Return tourist destinations from the existing
    other_spots table.

    Reviews and embedding vectors are intentionally
    excluded from the response.
    """

    try:
        connection = get_connection()

        if district:
            rows = connection.execute(
                """
                SELECT
                    id,
                    name,
                    district,
                    category,
                    rating,
                    popularity,
                    entry_fee,
                    lat,
                    lon
                FROM other_spots
                WHERE LOWER(TRIM(district)) = LOWER(TRIM(?))
                ORDER BY
                    popularity DESC,
                    rating DESC,
                    name ASC
                """,
                (district,)
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT
                    id,
                    name,
                    district,
                    category,
                    rating,
                    popularity,
                    entry_fee,
                    lat,
                    lon
                FROM other_spots
                ORDER BY
                    popularity DESC,
                    rating DESC,
                    name ASC
                """
            ).fetchall()

        connection.close()

        destinations = [
            {
                "id": row["id"],
                "name": row["name"],
                "district": row["district"],
                "category": row["category"],
                "rating": row["rating"],
                "popularity": row["popularity"],
                "entry_fee": row["entry_fee"],
                "latitude": row["lat"],
                "longitude": row["lon"]
            }
            for row in rows
        ]

        return {
            "count": len(destinations),
            "district": district,
            "destinations": destinations
        }

    except sqlite3.Error as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load destinations: {error}"
        )


@router.get("/districts")
def get_districts():
    """
    Return all districts that currently have
    destinations in other_spots.
    """

    try:
        connection = get_connection()

        rows = connection.execute(
            """
            SELECT DISTINCT TRIM(district) AS district
            FROM other_spots
            WHERE district IS NOT NULL
              AND TRIM(district) != ''
            ORDER BY district ASC
            """
        ).fetchall()

        connection.close()

        districts = [
            row["district"]
            for row in rows
        ]

        return {
            "count": len(districts),
            "districts": districts
        }

    except sqlite3.Error as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load districts: {error}"
        )