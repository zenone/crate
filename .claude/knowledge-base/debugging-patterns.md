# Debugging Patterns

Battle-tested approaches for finding and fixing bugs efficiently.

---

## The 3-Session Rule

**Pattern**: If a bug survives 3 dedicated debugging sessions without resolution, escalate or cut.

**Escalation Options**:
1. **Simplify**: Remove the buggy feature entirely (Upkeep removed TUI after 3+ sessions)
2. **Replace**: Use a different approach (switch libraries, rewrite from scratch)
3. **Isolate**: Create minimal reproduction to share with library maintainers
4. **Accept**: Document as known issue if low impact

**Why 3 Sessions?**:
- Session 1: Understand the bug, form hypotheses
- Session 2: Test hypotheses, try fixes
- Session 3: If still broken, the bug is either very deep or your approach is wrong

**Anti-pattern**: Spending session 4, 5, 6... on the same bug with minor variations of the same fix.

---

## Binary Search Debugging

**When**: Bug appeared "somewhere" in recent changes.

**Process**:
```bash
git log --oneline -20           # Find commit range
git bisect start
git bisect bad HEAD             # Current is broken
git bisect good abc123          # Known good commit
# Git checks out middle commit
# Test if bug exists
git bisect good                 # or git bisect bad
# Repeat until found
git bisect reset
```

**Automation**:
```bash
git bisect run ./test-script.sh  # Returns 0 for good, non-0 for bad
```

---

## Reproduce First, Fix Second

**Pattern**: Never attempt a fix until you can reliably reproduce the bug.

**Reproduction Checklist**:
- [ ] Can reproduce in test environment
- [ ] Can reproduce with minimal steps
- [ ] Reproduction is deterministic (same inputs → same bug)
- [ ] Have written a failing test that demonstrates bug

**Why This Matters**:
- No repro = shooting in the dark
- Failing test = proof the fix works
- Minimal repro = faster iteration

**Template for Bug Reports**:
```markdown
## Bug: [Brief Description]

**Reproduction Steps**:
1. Start with [state]
2. Do [action]
3. Observe [unexpected behavior]

**Expected**: [what should happen]
**Actual**: [what actually happens]

**Environment**: macOS 15.3, Python 3.12, [relevant versions]

**Minimal Reproduction**:
[code or commands to reproduce]
```

---

## Print Debugging (Don't Be Ashamed)

**When**: Debugger is overkill or unavailable.

**Effective Print Debugging**:
```python
# BAD: Meaningless output
print("here")
print("here 2")
print(x)

# GOOD: Contextual, greppable, removable
print(f"[DEBUG:auth] user_id={user_id} token_valid={is_valid}")
print(f"[DEBUG:cache] cache_hit={hit} key={cache_key}")
```

**Removal Pattern**:
```bash
# Find all debug prints
grep -rn "\[DEBUG:" src/

# Remove when done
sed -i '' '/\[DEBUG:/d' src/**/*.py
```

**Production Alternative**:
```python
import logging
logger = logging.getLogger(__name__)
logger.debug(f"cache_hit={hit} key={cache_key}")  # Controlled by log level
```

---

## State Inspection Patterns

### For Web Apps (Browser DevTools)
```javascript
// Dump state to console
console.log(JSON.stringify(appState, null, 2));

// Monitor state changes
const originalSetState = setState;
setState = (newState) => {
    console.log('[STATE CHANGE]', newState);
    originalSetState(newState);
};
```

### For Python (Interactive Debugging)
```python
# Drop into debugger at any point
import pdb; pdb.set_trace()

# Or with ipdb for better UX
import ipdb; ipdb.set_trace()

# Python 3.7+: built-in breakpoint
breakpoint()
```

### For File-Based State
```bash
# Watch file changes in real-time
fswatch -r ~/.appname/state/ | while read f; do echo "Changed: $f"; cat "$f"; done

# Or with entr
ls ~/.appname/state/*.json | entr -c cat /_
```

---

## Race Condition Debugging

**Symptoms**:
- Works sometimes, fails sometimes
- Fails under load but works in isolation
- "Heisenbug" - disappears when you add logging

**Diagnosis**:
```python
import threading
import time

# Add artificial delays to expose race
def suspicious_function():
    print(f"[RACE] Thread {threading.current_thread().name} entering")
    time.sleep(0.1)  # Expose race window
    # ... code ...
    print(f"[RACE] Thread {threading.current_thread().name} exiting")
```

**Common Fixes**:
- Add locks around shared state
- Use thread-safe data structures (queue.Queue, collections.deque)
- Make operations atomic
- Use database transactions

---

## Memory Leak Debugging

**Symptoms**:
- Memory grows over time
- Eventually crashes with OOM
- Gets slower the longer it runs

**Python Tools**:
```python
# Track object counts
import gc
gc.collect()
print(len(gc.get_objects()))

# Find what's holding references
import objgraph
objgraph.show_most_common_types(limit=20)
objgraph.show_backrefs(obj, max_depth=3)

# Memory profiler
# pip install memory_profiler
@profile
def my_function():
    ...
# Run: python -m memory_profiler script.py
```

**Common Causes**:
- Growing lists/dicts never cleared
- Event listeners never removed
- Circular references (especially with closures)
- Caches without eviction policy

---

## Timeout/Hang Debugging

**Symptoms**:
- Process appears frozen
- No output, no crash, just... nothing

**Diagnosis**:
```bash
# What's the process doing?
ps aux | grep [p]rocess_name

# System calls (macOS)
sudo dtruss -p <pid>

# System calls (Linux)
strace -p <pid>

# Python: dump all thread stacks
import faulthandler
faulthandler.enable()
# Then send SIGABRT: kill -ABRT <pid>
```

**Common Causes**:
- Deadlock (two locks, wrong order)
- Blocking I/O without timeout
- Infinite loop (missing break condition)
- Waiting for resource that never arrives

---

## Async/Await Debugging

**Symptoms**:
- Callbacks never fire
- Promises never resolve
- async function returns immediately without waiting

**Python asyncio**:
```python
import asyncio

# Enable debug mode
asyncio.get_event_loop().set_debug(True)

# See pending tasks
for task in asyncio.all_tasks():
    print(f"Task: {task.get_name()} done={task.done()}")
```

**JavaScript**:
```javascript
// Forgot to await?
async function buggy() {
    fetch('/api');  // ← Missing await!
    console.log('done');  // Runs before fetch completes
}

// Pattern: Always await or explicitly fire-and-forget
async function correct() {
    await fetch('/api');
    console.log('done');
}
```

---

## The "Works on My Machine" Checklist

When code works locally but fails elsewhere:

- [ ] **Environment variables**: Are all required vars set?
- [ ] **File paths**: Absolute vs relative? OS-specific separators?
- [ ] **Dependencies**: Same versions? (`pip freeze` / `package-lock.json`)
- [ ] **Permissions**: File/directory permissions different?
- [ ] **Network**: Firewall? DNS? Proxy?
- [ ] **Time/Timezone**: Date formatting? Timezone assumptions?
- [ ] **Locale**: Different character encoding? Sort order?
- [ ] **Case sensitivity**: macOS default is case-insensitive; Linux is case-sensitive

---

## Quick Reference: Debug Commands

```bash
# Python
python -m pdb script.py          # Start in debugger
python -m trace --trace script.py # Print every line executed

# Node.js
node --inspect script.js         # Chrome DevTools debugging
node --inspect-brk script.js     # Break on first line

# General
lsof -p <pid>                    # Open files/sockets
netstat -an | grep <port>        # Network connections
```
