from monday import MondayClient
from config import MONDAY_API_KEY, DEALS_BOARD_ID, WORK_ORDERS_BOARD_ID

client = MondayClient(MONDAY_API_KEY)


def fetch_deals():
    try:
        board = client.boards.fetch_board_by_id(DEALS_BOARD_ID)
        items = board.get_items()
        return [item.to_dict() for item in items]
    except Exception as e:
        print(f"Error fetching deals: {str(e)}")
        return []


def fetch_work_orders():
    try:
        board = client.boards.fetch_board_by_id(WORK_ORDERS_BOARD_ID)
        items = board.get_items()
        return [item.to_dict() for item in items]
    except Exception as e:
        print(f"Error fetching work orders: {str(e)}")
        return []
