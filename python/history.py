"""
===================================================================
Author/Maker : jihoonkimtech
Project      : Raw2Insight
File         : history.py
Purpose      : In-memory sensor history for fast UI updates and AI input
===================================================================
"""
import time
from collections import deque

# Seconds of raw samples kept for the dashboard
HISTORY_SEC = 60.0
# Bucket length for AI input (same as the former InfluxDB 2s aggregation)
AI_BUCKET_SEC = 2.0
# Number of AI buckets (300 x 2s = 10 minutes)
AI_BUCKETS = 300
# Sliding window for the smoothed "stable" line
SMOOTH_SEC = 2.0
# Averaging window for DB writes
DB_WRITE_SEC = 1.0


class _SensorTrack:
    def __init__(self):
        self.raw = deque()                         # (t, value)
        self.buckets = deque(maxlen=AI_BUCKETS)    # closed 2s means, newest last
        self.bucket_start = None
        self.bucket_sum = 0.0
        self.bucket_n = 0
        self.db_start = None
        self.db_sum = 0.0
        self.db_n = 0
        self.seeded = False


class SensorHistory:
    def __init__(self):
        self.tracks = {}

    def _track(self, name):
        if name not in self.tracks:
            self.tracks[name] = _SensorTrack()
        return self.tracks[name]

    def seed(self, name, values_desc):
        # Preload AI buckets from DB (newest first) so the model survives restarts
        tr = self._track(name)
        if tr.seeded:
            return
        tr.seeded = True
        for v in reversed(values_desc[:AI_BUCKETS]):
            tr.buckets.append(float(v))

    def is_seeded(self, name):
        return name in self.tracks and self.tracks[name].seeded

    def add(self, name, value, now=None):
        # Append one sample, returns the smoothed value
        now = time.time() if now is None else now
        tr = self._track(name)
        v = float(value)

        tr.raw.append((now, v))
        while tr.raw and now - tr.raw[0][0] > HISTORY_SEC:
            tr.raw.popleft()

        # Close the AI bucket when its window has passed
        if tr.bucket_start is None:
            tr.bucket_start = now
        elif now - tr.bucket_start >= AI_BUCKET_SEC:
            if tr.bucket_n:
                tr.buckets.append(tr.bucket_sum / tr.bucket_n)
            tr.bucket_start, tr.bucket_sum, tr.bucket_n = now, 0.0, 0
        tr.bucket_sum += v
        tr.bucket_n += 1

        # Accumulate for the averaged DB write
        if tr.db_start is None:
            tr.db_start = now
        tr.db_sum += v
        tr.db_n += 1

        return self.smoothed(name, now)

    def smoothed(self, name, now=None):
        # Mean of samples in the last SMOOTH_SEC
        tr = self.tracks.get(name)
        if not tr or not tr.raw:
            return None
        now = tr.raw[-1][0] if now is None else now
        total, n = 0.0, 0
        for t, v in reversed(tr.raw):
            if now - t > SMOOTH_SEC:
                break
            total += v
            n += 1
        return total / n if n else tr.raw[-1][1]

    def ai_values(self, name):
        # Newest first: current partial bucket, then closed buckets
        tr = self.tracks.get(name)
        if not tr:
            return []
        values = []
        if tr.bucket_n:
            values.append(tr.bucket_sum / tr.bucket_n)
        values.extend(reversed(tr.buckets))
        return values

    def pop_db_writes(self, now=None):
        # Return {name: mean} for tracks whose DB window elapsed
        now = time.time() if now is None else now
        out = {}
        for name, tr in self.tracks.items():
            if tr.db_n and now - tr.db_start >= DB_WRITE_SEC:
                out[name] = tr.db_sum / tr.db_n
                tr.db_start, tr.db_sum, tr.db_n = now, 0.0, 0
        return out

    def points(self, name):
        # Dashboard points as [epoch_ms, value, smoothed] using a sliding SMOOTH_SEC window
        tr = self.tracks.get(name)
        if not tr:
            return []
        out = []
        window = deque()
        total = 0.0
        for t, v in tr.raw:
            window.append((t, v))
            total += v
            while t - window[0][0] > SMOOTH_SEC:
                total -= window.popleft()[1]
            out.append([int(t * 1000), round(v, 3), round(total / len(window), 3)])
        return out

    def prune(self, live_names):
        # Forget deleted sensors
        for name in list(self.tracks.keys()):
            if name not in live_names:
                del self.tracks[name]
