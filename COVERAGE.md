# CESP Category Coverage

## Summary

| Pack | session.start | task.acknowledge | task.complete | task.error | input.required | resource.limit | user.spam |
|---|---|---|---|---|---|---|---|
| cute-minimal | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| dreamy-minimal | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| modern-varied | 3 | 5 | 6 | 4 | 5 | 3 | 2 |
| nezuai-varied | 2 | 2 | 2 | 3 | 2 | 2 | 4 |
| nightflame-minimal | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

## Detail

### cute-minimal

- **session.start** (1): Pause
- **task.acknowledge** (1): Confirm
- **task.complete** (1): Cancel
- **task.error** (1): Cancel (low)
- **input.required** (1): Hover
- **resource.limit** (1): Pause (low)
- **user.spam** (1): Hover (low)

### dreamy-minimal

- **session.start** (1): Soft dreamy beep (alt)
- **task.acknowledge** (1): Correct blips
- **task.complete** (1): Soft dreamy beep
- **task.error** (1): Menu beep
- **input.required** (1): Positive blip
- **resource.limit** (1): Menu beep (low)
- **user.spam** (1): Soft dreamy beep (low)

### modern-varied

- **session.start** (3): Popup open (bright), Popup open (neutral), Session ping
- **task.acknowledge** (5): Hightech confirm 1, Hightech confirm 2, Hightech confirm 3, Menu chime, Menu ping
- **task.complete** (6): Success alert 1, Success alert 2, Success alert 3, Success alert 4, Success alert 5, Success alert 6
- **task.error** (4): UI error buzz, Popup close (dark), Popup open (harsh), UI misc buzz
- **input.required** (5): Notification 1, Notification 2, Hightech notification 1, Hightech notification 2, Hightech notification 3
- **resource.limit** (3): Low warning tone, Warning sweep, Depleted tone
- **user.spam** (2): Menu scroll, Menu whoosh (dark)

### nezuai-varied

- **session.start** (2): Swelling whoosh, Intense whoosh
- **task.acknowledge** (2): Short buzz, Decaying beep
- **task.complete** (2): Positive whoosh, Neutral beep
- **task.error** (3): Low thud, Negative beep, High negative whoosh
- **input.required** (2): High whoosh, Long high beep
- **resource.limit** (2): Warning sweep, Low warning tone
- **user.spam** (4): Low buzz, Dismissive whoosh, Negative whoosh, Long low beep

### nightflame-minimal

- **session.start** (1): Attention whoosh
- **task.acknowledge** (1): Attention whoosh (low)
- **task.complete** (1): Confirmation tone
- **task.error** (1): Descending tone
- **input.required** (1): Session sweep
- **resource.limit** (1): Ascending tone
- **user.spam** (1): Session sweep (low)
