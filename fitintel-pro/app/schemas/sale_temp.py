# ============================================================
# SALE PACKAGE (комплексная продажа)
# ============================================================

class SalePackageRequest(BaseModel):
    """Запрос на комплексную продажу (пакет услуг)"""
    client_id: str
    items: List[SaleItemCreate]
    discount_percent: Optional[int] = Field(0, ge=0, le=100)
    payment_method: str
    model_config = ConfigDict(str_strip_whitespace=True)


class SalePackageResponse(BaseModel):
    """Ответ на комплексную продажу"""
    success: bool
    sale_id: Optional[str] = None
    total_amount: float
    discount_amount: float
    final_amount: float
    items_sold: int
    receipt_number: Optional[str] = None
    model_config = ConfigDict(str_strip_whitespace=True)

