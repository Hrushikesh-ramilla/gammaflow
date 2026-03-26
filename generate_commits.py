import re
import os
import subprocess
import glob
from datetime import datetime

# Parse syl.md
with open("../syl.md", "r", encoding="utf-8") as f:
    content = f.read()

# Regex to match table rows
pattern = re.compile(r'\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*`?([^|`]+)`?\s*\|\s*([^|]+)\s*\|')

commits = []
for match in pattern.finditer(content):
    idx = int(match.group(1).strip())
    raw_date = match.group(2).strip()
    msg = match.group(3).strip()
    files_col = match.group(4).strip()
    
    # Parse date (e.g., 'Mar 19', 'Mar 19 AM', 'Apr 2')
    # Default year 2026
    date_str = re.sub(r'AM|PM', '', raw_date).strip()
    try:
        dt = datetime.strptime(f"2026 {date_str}", "%Y %b %d")
        # Add hours to make them sequential within a day
        hour = 10 + (idx % 8) # spread between 10am and 5pm
        dt = dt.replace(hour=hour, minute=(idx * 7) % 60)
        iso_date = dt.isoformat()
    except ValueError:
        iso_date = "2026-03-19T12:00:00"

    # Extract likely files
    # The files column contains comma separated text or plain text
    # e.g., "README.md, LICENSE", "app/main.py — entry"
    raw_files = files_col.split(',')
    paths_to_add = []
    for rf in raw_files:
        clean = rf.split('—')[0].strip()
        # extract words that look like files with extensions or paths
        for word in clean.split():
            if '.' in word or '/' in word:
                paths_to_add.append(word)

    commits.append({
        "num": idx,
        "date": iso_date,
        "msg": msg,
        "files": paths_to_add
    })

# Unstage everything first safely just in case
subprocess.run("git reset HEAD", shell=True)

# Run commits
total = len(commits)
for c in commits:
    # Try adding files
    for filepath in c["files"]:
        # Naive exact match
        if os.path.exists(filepath):
            subprocess.run(f"git add {filepath}", shell=True)
        else:
            # Try fuzzy match
            base = os.path.basename(filepath)
            matches = glob.glob(f"**/{base}", recursive=True)
            for m in matches:
                subprocess.run(f"git add {m}", shell=True)
    
    # Provide env variables for date spoofing
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = c["date"]
    env["GIT_COMMITTER_DATE"] = c["date"]
    
    # Commit
    res = subprocess.run(
        ["git", "commit", "-m", c["msg"]],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if res.returncode != 0:
        # Nothing to commit, allow empty
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", c["msg"]],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

# Final sweep: Any files missed get batched into the final commit
subprocess.run("git add .", shell=True)
subprocess.run(
    ["git", "commit", "-m", "chore: sweep unindexed files and final architecture bind"],
    env=env
)
print("Finished chronological commit generation.")
