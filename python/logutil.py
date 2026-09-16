"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : logutil.py
Purpose      : Debug log switch (per-cycle logs slow down a 5Hz loop)
===================================================================
"""
import os

# Set RAW2INSIGHT_DEBUG=1 to print per-cycle debug logs
DEBUG = os.environ.get("RAW2INSIGHT_DEBUG", "0") == "1"


def dbg(*args, **kwargs):
    # Print only when debug logging is enabled
    if DEBUG:
        print(*args, **kwargs)
