from monday import MondayClient
from app.config import MONDAY_API_KEY, DEALS_BOARD_ID, WORK_ORDERS_BOARD_ID

client = MondayClient(MONDAY_API_KEY)


def fetch_deals():
    try:
        resp = client.boards.fetch_items_by_board_id(DEALS_BOARD_ID)
        if isinstance(resp, dict):
            try:
                boards = resp.get('data', {}).get('boards', [])
                if boards:
                    items = boards[0].get('items_page', {}).get('items', [])
                    return items
            except Exception:
                pass
        try:
            return list(resp)
        except Exception:
            return []
    except Exception as e:
        print(f"Error fetching deals: {str(e)}")
        return []


def fetch_work_orders():
    try:
        resp = client.boards.fetch_items_by_board_id(WORK_ORDERS_BOARD_ID)
        if isinstance(resp, dict):
            try:
                boards = resp.get('data', {}).get('boards', [])
                if boards:
                    items = boards[0].get('items_page', {}).get('items', [])
                    return items
            except Exception:
                pass
        try:
            return list(resp)
        except Exception:
            return []
    except Exception as e:
        print(f"Error fetching work orders: {str(e)}")
        return []


def fetch_columns_by_board(board_id):
    try:
        resp = client.boards.fetch_columns_by_board_id(board_id)
        if isinstance(resp, dict):
            try:
                boards = resp.get('data', {}).get('boards', [])
                if boards:
                    cols = boards[0].get('columns', [])
                    return cols
            except Exception:
                pass
        try:
            return list(resp)
        except Exception:
            return []
    except Exception as e:
        print(f"Error fetching columns: {str(e)}")
        return []


def fetch_deals_columns():
    return fetch_columns_by_board(DEALS_BOARD_ID)


def fetch_work_orders_columns():
    return fetch_columns_by_board(WORK_ORDERS_BOARD_ID)
