"""routes/sales.py — GET /sales"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from schemas.events import SalesBreakdownResponse

router = APIRouter()


@router.get("/sales", response_model=SalesBreakdownResponse, summary="Sales breakdown by department and salesperson")
def get_sales(db: Session = Depends(get_db)):
    """
    Returns sales analytics from the Brigade Road CSV:

    - **by_department**: revenue and order count per product category
    - **by_salesperson**: revenue and orders attributed to each staff member
    - **top_brands**: best-selling brands by revenue

    This data comes from the 22-order Brigade Road CSV loaded at startup.
    """
    return crud.get_sales_breakdown(db)
