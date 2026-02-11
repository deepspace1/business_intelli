from datetime import datetime


def get_current_quarter_range():
    today = datetime.now()
    q = (today.month - 1) // 3 + 1
    year = today.year
    
    quarters = {
        1: (datetime(year, 1, 1), datetime(year, 3, 31)),
        2: (datetime(year, 4, 1), datetime(year, 6, 30)),
        3: (datetime(year, 7, 1), datetime(year, 9, 30)),
        4: (datetime(year, 10, 1), datetime(year, 12, 31))
    }
    return quarters[q]


def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).split('T')[0], "%Y-%m-%d")
    except:
        return None


def compute_deals_metrics(deals):
    if not deals:
        return {"total_pipeline": 0, "deal_count": 0, "by_sector": {}}
    
    def safe_amount(x):
        try:
            return float(x or 0)
        except Exception:
            return 0

    metrics = {
        "total_pipeline": sum(safe_amount(d.get("amount", 0)) for d in deals),
        "deal_count": len(deals),
        "by_sector": {}
    }
    
    for deal in deals:
        sector = deal.get("sector", "unknown") or 'unknown'
        if sector not in metrics["by_sector"]:
            metrics["by_sector"][sector] = {"pipeline": 0, "count": 0}
        metrics["by_sector"][sector]["pipeline"] += safe_amount(deal.get("amount", 0))
        metrics["by_sector"][sector]["count"] += 1
    
    return metrics


def compute_deals_metrics_by_quarter(deals):
    if not deals:
        return {"pipeline": 0, "count": 0}
    
    start, end = get_current_quarter_range()
    filtered = [d for d in deals if parse_date(d.get("close_date")) and start <= parse_date(d.get("close_date")) <= end]
    
    return {
        "pipeline": sum(d.get("amount", 0) for d in filtered),
        "count": len(filtered)
    }


def compute_work_orders_metrics(work_orders):
    if not work_orders:
        return {"total_revenue": 0, "active_count": 0, "by_status": {}}
    
    metrics = {
        "total_revenue": sum(w.get("revenue", 0) for w in work_orders),
        "active_count": len([w for w in work_orders if w.get("status", "").lower() in ["active", "in progress"]]),
        "by_status": {}
    }
    
    for wo in work_orders:
        status = wo.get("status", "unknown").lower()
        if status not in metrics["by_status"]:
            metrics["by_status"][status] = {"revenue": 0, "count": 0}
        metrics["by_status"][status]["revenue"] += wo.get("revenue", 0)
        metrics["by_status"][status]["count"] += 1
    
    return metrics


def get_leadership_summary(deals, work_orders):
    deals_metrics = compute_deals_metrics(deals)
    wo_metrics = compute_work_orders_metrics(work_orders)
    quarter_metrics = compute_deals_metrics_by_quarter(deals)
    
    return {
        "total_pipeline": deals_metrics["total_pipeline"],
        "quarter_pipeline": quarter_metrics["pipeline"],
        "total_revenue": wo_metrics["total_revenue"],
        "active_deals": deals_metrics["deal_count"],
        "active_work_orders": wo_metrics["active_count"],
        "top_sectors": sorted(
            deals_metrics["by_sector"].items(),
            key=lambda x: x[1]["pipeline"],
            reverse=True
        )[:3]
    }
