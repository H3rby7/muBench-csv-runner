from Counter import Counter
from datetime import datetime

global experiment_id
experiment_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
global pending_requests
pending_requests = Counter()
global timing_error_requests
timing_error_requests = Counter()
global processed_requests
processed_requests = Counter()
global error_requests
error_requests = Counter()
