
import os

# Load configuration from environment variables. Do NOT store secrets in this file
# in version control. For local development copy `app/config.example.py` to
# `app/config.py` or set environment variables (recommended).

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_API_URL = os.getenv("MONDAY_API_URL", "https://api.monday.com/v2")

# Board IDs can be provided via environment variables. The examples used
# previously were numeric strings; keep them as strings.
DEALS_BOARD_ID = os.getenv("DEALS_BOARD_ID")
WORK_ORDERS_BOARD_ID = os.getenv("WORK_ORDERS_BOARD_ID")

# Backwards-compatibility alias if other parts of the code expect a different
# variable name (avoid relying on this long-term).
WORKORDERS_BOARD_ID = WORK_ORDERS_BOARD_ID

def validate_config(raise_on_missing=False):
	"""Return list of missing required variables. If raise_on_missing is True
	raise RuntimeError when any required var is missing.
	"""
	required = [
		"GEMINI_API_KEY",
		"MONDAY_API_KEY",
		"DEALS_BOARD_ID",
		"WORK_ORDERS_BOARD_ID",
	]
	missing = [k for k in required if not globals().get(k)]
	if missing and raise_on_missing:
		raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
	return missing
