# Run the worker
nohup python3 worker.py > worker.log 2>&1 &

# Check worker status
ps aux | grep worker.py

# Terminate the worker
pkill -f worker.py
