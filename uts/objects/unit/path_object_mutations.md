# PathObject Write Operations Tests

Spec points: `RTPO15`–`RTPO18`, `RTPO3c2`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel` and builder functions.

---

## RTPO15 - set() delegates to InternalLiveMap#set

**Test ID**: `objects/unit/RTPO15/set-delegates-to-map-0`

| Spec | Requirement |
|------|-------------|
| RTPO15b | Checks write API preconditions per RTO26 |
| RTPO15c | Resolves path, on failure throws RTPO3c2 |
| RTPO15d | InternalLiveMap -> delegates to InternalLiveMap#set (RTLM20) |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.set("name", "Bob")
```

### Assertions
```pseudo
ASSERT root.get("name").value() == "Bob"
```

---

## RTPO15 - set() on nested path

**Test ID**: `objects/unit/RTPO15/set-nested-path-0`

| Spec | Requirement |
|------|-------------|
| RTPO15a2 | value accepts same types as InternalLiveMap#set (RTLM20): primitives and LiveCounter/LiveMap |
| RTPO15b | Checks write API preconditions per RTO26 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("profile").set("email", "bob@example.com")
```

### Assertions
```pseudo
ASSERT root.get("profile").get("email").value() == "bob@example.com"
```

---

## RTPO15d - set() on non-InternalLiveMap throws 92007

**Test ID**: `objects/unit/RTPO15d/set-non-map-throws-0`

| Spec | Requirement |
|------|-------------|
| RTPO15b | Checks write API preconditions per RTO26 |
| RTPO15e | Not InternalLiveMap -> throws 92007 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("score").set("key", "value") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTPO16 - remove() delegates to InternalLiveMap#remove

**Test ID**: `objects/unit/RTPO16/remove-delegates-to-map-0`

| Spec | Requirement |
|------|-------------|
| RTPO16b | Checks write API preconditions per RTO26 |
| RTPO16c | Resolves path, on failure throws RTPO3c2 |
| RTPO16d | InternalLiveMap -> delegates to InternalLiveMap#remove (RTLM21) |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.remove("name")
```

### Assertions
```pseudo
ASSERT root.get("name").value() == null
```

---

## RTPO16d - remove() on non-InternalLiveMap throws 92007

**Test ID**: `objects/unit/RTPO16d/remove-non-map-throws-0`

| Spec | Requirement |
|------|-------------|
| RTPO16b | Checks write API preconditions per RTO26 |
| RTPO16e | Not InternalLiveMap -> throws 92007 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("score").remove("key") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTPO17 - increment() delegates to InternalLiveCounter#increment

**Test ID**: `objects/unit/RTPO17/increment-delegates-to-counter-0`

| Spec | Requirement |
|------|-------------|
| RTPO17b | Checks write API preconditions per RTO26 |
| RTPO17c | Resolves path, on failure throws RTPO3c2 |
| RTPO17d | InternalLiveCounter -> delegates to InternalLiveCounter#increment (RTLC12) |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("score").increment(25)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 125
```

---

## RTPO17 - increment() defaults to 1

**Test ID**: `objects/unit/RTPO17/increment-default-amount-0`

| Spec | Requirement |
|------|-------------|
| RTPO17a1 | amount defaults to 1 |
| RTPO17b | Checks write API preconditions per RTO26 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("score").increment()
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 101
```

---

## RTPO17d - increment() on non-InternalLiveCounter throws 92007

**Test ID**: `objects/unit/RTPO17d/increment-non-counter-throws-0`

| Spec | Requirement |
|------|-------------|
| RTPO17b | Checks write API preconditions per RTO26 |
| RTPO17e | Not InternalLiveCounter -> throws 92007 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.increment(5) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTPO18 - decrement() delegates to InternalLiveCounter#decrement

**Test ID**: `objects/unit/RTPO18/decrement-delegates-to-counter-0`

| Spec | Requirement |
|------|-------------|
| RTPO18b | Checks write API preconditions per RTO26 |
| RTPO18c | Resolves path, on failure throws RTPO3c2 |
| RTPO18d | InternalLiveCounter -> delegates to InternalLiveCounter#decrement (RTLC13) |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("score").decrement(10)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 90
```

---

## RTPO18 - decrement() defaults to 1

**Test ID**: `objects/unit/RTPO18/decrement-default-amount-0`

| Spec | Requirement |
|------|-------------|
| RTPO18a1 | amount defaults to 1 |
| RTPO18b | Checks write API preconditions per RTO26 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("score").decrement()
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 99
```

---

## RTPO18d - decrement() on non-InternalLiveCounter throws 92007

**Test ID**: `objects/unit/RTPO18d/decrement-non-counter-throws-0`

| Spec | Requirement |
|------|-------------|
| RTPO18b | Checks write API preconditions per RTO26 |
| RTPO18e | Not InternalLiveCounter -> throws 92007 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.decrement(5) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTPO3c2 - set() on unresolvable path throws 92005

**Test ID**: `objects/unit/RTPO3c2/set-unresolvable-throws-0`

| Spec | Requirement |
|------|-------------|
| RTPO15b | Checks write API preconditions per RTO26 |
| RTPO3c2 | Write operations on unresolvable path throw ErrorInfo with statusCode 400, code 92005 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("nonexistent").get("deep").set("key", "value") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92005
ASSERT error.statusCode == 400
```

---

## RTPO3c2 - increment() on unresolvable path throws 92005

**Test ID**: `objects/unit/RTPO3c2/increment-unresolvable-throws-0`

| Spec | Requirement |
|------|-------------|
| RTPO17b | Checks write API preconditions per RTO26 |
| RTPO3c2 | Write operations on unresolvable path throw ErrorInfo with statusCode 400, code 92005 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("nonexistent").increment(5) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92005
ASSERT error.statusCode == 400
```
