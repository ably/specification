# PathObject Write Operations Tests

Spec points: `RTPO15`–`RTPO18`, `RTPO3c2`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel` and builder functions.

---

## RTPO15 - set() delegates to LiveMap#set

**Test ID**: `objects/unit/RTPO15/set-delegates-to-map-0`

| Spec | Requirement |
|------|-------------|
| RTPO15b | Resolves path, on failure throws RTPO3c2 |
| RTPO15c | LiveMap -> delegates to LiveMap#set |

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

## RTPO15d - set() on non-LiveMap throws 92007

**Test ID**: `objects/unit/RTPO15d/set-non-map-throws-0`

**Spec requirement:** If resolved value is not a LiveMap, throw 92007.

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

## RTPO16 - remove() delegates to LiveMap#remove

**Test ID**: `objects/unit/RTPO16/remove-delegates-to-map-0`

| Spec | Requirement |
|------|-------------|
| RTPO16b | Resolves path, on failure throws RTPO3c2 |
| RTPO16c | LiveMap -> delegates to LiveMap#remove |

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

## RTPO16d - remove() on non-LiveMap throws 92007

**Test ID**: `objects/unit/RTPO16d/remove-non-map-throws-0`

**Spec requirement:** If resolved value is not a LiveMap, throw 92007.

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

## RTPO17 - increment() delegates to LiveCounter#increment

**Test ID**: `objects/unit/RTPO17/increment-delegates-to-counter-0`

| Spec | Requirement |
|------|-------------|
| RTPO17b | Resolves path, on failure throws RTPO3c2 |
| RTPO17c | LiveCounter -> delegates to LiveCounter#increment |

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

**Spec requirement:** amount defaults to 1.

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

## RTPO17d - increment() on non-LiveCounter throws 92007

**Test ID**: `objects/unit/RTPO17d/increment-non-counter-throws-0`

**Spec requirement:** If resolved value is not a LiveCounter, throw 92007.

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

## RTPO18 - decrement() delegates to LiveCounter#decrement

**Test ID**: `objects/unit/RTPO18/decrement-delegates-to-counter-0`

| Spec | Requirement |
|------|-------------|
| RTPO18b | Resolves path, on failure throws RTPO3c2 |
| RTPO18c | LiveCounter -> delegates to LiveCounter#decrement |

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

**Spec requirement:** amount defaults to 1.

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

## RTPO18d - decrement() on non-LiveCounter throws 92007

**Test ID**: `objects/unit/RTPO18d/decrement-non-counter-throws-0`

**Spec requirement:** If resolved value is not a LiveCounter, throw 92007.

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

**Spec requirement:** For write operations, if path resolution fails, throw 92005.

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
```

---

## RTPO3c2 - increment() on unresolvable path throws 92005

**Test ID**: `objects/unit/RTPO3c2/increment-unresolvable-throws-0`

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
```
