import glob
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

log_dir = "/home/cxiong/pong_ppo/logs/ppo_pong/"
# Find the most recent event file to determine the latest run
event_files = glob.glob(f"{log_dir}**/events.out*", recursive=True)
if not event_files:
    print("No event files found.")
    exit()

# Sort by modification time to get the latest run directory
latest_file = max(event_files, key=os.path.getmtime)
latest_run_dir = os.path.dirname(latest_file)
print(f"Analyzing latest run in: {latest_run_dir}")

ea = EventAccumulator(latest_run_dir)
ea.Reload()

try:
    rewards = ea.Scalars('rollout/ep_rew_mean')
    if not rewards:
        print("No 'rollout/ep_rew_mean' found in logs.")
    else:
        latest = rewards[-1]
        print(f"Step: {latest.step} | Mean Reward: {latest.value:.2f}")
except Exception as e:
    print(f"Error parsing logs: {e}")
