"""routes/anomalies.py — GET /anomalies"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from schemas.events import AnomaliesResponse, Anomaly

router = APIRouter()


@router.get("/anomalies", response_model=AnomaliesResponse, summary="Detected anomalies")
def get_anomalies(db: Session = Depends(get_db)):
    """
    Returns detected store anomalies:

    - **crowd_surge**: unusually high entries in a short time window
    - **unusual_dwell**: person staying in a zone far longer than average
    - **empty_store**: no customer activity for extended period
    """
    raw = crud.get_anomalies(db)
    anomalies = [Anomaly(**a) for a in raw]
    return AnomaliesResponse(anomalies=anomalies, total=len(anomalies))
