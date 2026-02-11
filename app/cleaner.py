import logging
import pandas as pd

logger = logging.getLogger(__name__)


def parse_item(item):
    data = item if isinstance(item, dict) else item.to_dict() if hasattr(item, 'to_dict') else {}
    cols = {}
    for cv in data.get('column_values', []):
        cid = cv.get('id') or cv.get('column', {}).get('id')
        if not cid:
            continue
        # prefer text then value
        val = cv.get('text')
        if val is None:
            val = cv.get('value')
        cols[cid] = val
    return cols


def build_id_title_map(columns_meta):
    id_to_title = {}
    if not columns_meta:
        return id_to_title
    for c in columns_meta:
        cid = c.get('id')
        title = (c.get('title') or c.get('name') or '')
        if cid:
            id_to_title[cid] = title.lower()
    return id_to_title


def find_col_id_by_keywords(id_to_title, keywords):
    for cid, title in id_to_title.items():
        for kw in keywords:
            if kw in title:
                return cid
    return None


def safe_number(x):
    if x is None:
        return 0.0
    try:
        s = str(x)
        s = s.replace('$', '').replace(',', '').strip()
        return float(s) if s else 0.0
    except Exception as e:
        logger.error('safe_number parse error for %r: %s', x, e)
        return 0.0


def to_date(x):
    try:
        return pd.to_datetime(x, errors='coerce')
    except Exception as e:
        logger.error('date parse error for %r: %s', x, e)
        return pd.NaT


def clean_deals(raw_items, columns_meta=None):
    """Return list of dicts with keys: name, amount, sector, close_date, stage"""
    if not raw_items:
        return []

    id_to_title = build_id_title_map(columns_meta)
    # Print column metadata once for verification
    try:
        print("[clean_deals] column id->title mapping:", id_to_title)
    except Exception:
        pass
    amount_col = find_col_id_by_keywords(id_to_title, ['amount', 'value'])
    # Only map sector when a column title explicitly contains these keywords
    sector_col = find_col_id_by_keywords(id_to_title, ['sector', 'industry', 'vertical', 'segment'])
    close_col = find_col_id_by_keywords(id_to_title, ['close'])
    stage_col = find_col_id_by_keywords(id_to_title, ['stage', 'status'])

    cleaned = []
    for item in raw_items:
        try:
            cols = parse_item(item)
            name = item.get('name') if isinstance(item, dict) else getattr(item, 'name', '')
            amount = safe_number(cols.get(amount_col)) if amount_col else 0.0
            # Strict sector mapping: do NOT guess from other columns. If no sector column, mark 'unknown'.
            if sector_col:
                raw_sector = cols.get(sector_col) or ''
                sector = raw_sector.strip().lower()
                sector = sector if sector else 'unknown'
            else:
                sector = 'unknown'
            close_date = to_date(cols.get(close_col)) if close_col else pd.NaT
            # Stage/status only mapped when a column explicitly named 'stage' or 'status'
            stage = (cols.get(stage_col) or '') if stage_col else ''

            cleaned.append({
                'name': name or '',
                'amount': amount,
                'sector': sector,
                'close_date': close_date,
                'stage': (stage or '').strip()
            })
        except Exception as e:
            logger.exception('Error cleaning deal item: %s', e)
    return cleaned


def clean_work_orders(raw_items, columns_meta=None):
    """Return list of dicts with keys: name, revenue, status, start_date, end_date"""
    if not raw_items:
        return []

    id_to_title = build_id_title_map(columns_meta)
    revenue_col = find_col_id_by_keywords(id_to_title, ['revenue'])
    status_col = find_col_id_by_keywords(id_to_title, ['status', 'state'])
    start_col = find_col_id_by_keywords(id_to_title, ['start'])
    end_col = find_col_id_by_keywords(id_to_title, ['end'])

    cleaned = []
    for item in raw_items:
        try:
            cols = parse_item(item)
            name = item.get('name') if isinstance(item, dict) else getattr(item, 'name', '')
            revenue = safe_number(cols.get(revenue_col)) if revenue_col else 0.0
            status = (cols.get(status_col) or '') if status_col else ''
            start_date = to_date(cols.get(start_col)) if start_col else pd.NaT
            end_date = to_date(cols.get(end_col)) if end_col else pd.NaT

            cleaned.append({
                'name': name or '',
                'revenue': revenue,
                'status': (status or '').strip().lower(),
                'start_date': start_date,
                'end_date': end_date
            })
        except Exception as e:
            logger.exception('Error cleaning work order item: %s', e)
    return cleaned
