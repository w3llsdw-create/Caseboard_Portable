# Focus History Logging Feature

## Overview

The Focus History Logging feature automatically tracks all changes to the "Current Focus" field for each case. Every time you update what you're working on for a case, the system logs that change with a timestamp, creating a complete history of case focus updates.

## How It Works

### Automatic Logging

When you update the "Current Focus" (also called `current_task`) field for any case:
1. The new focus text is automatically logged with a timestamp
2. The entry is stored in a per-case log file in `data/focus_logs/{case-id}.json`
3. Duplicate entries (same text as previous) are automatically skipped
4. Empty focus entries are not logged

### Viewing Focus History

#### Terminal UI (Textual App)

Press **H** (History) when a case is selected to view its complete focus history:
- Shows all focus updates in reverse chronological order (most recent first)
- Displays timestamp, actor, and focus text for each entry
- Accessible via the main caseboard app

#### Web Dashboard API

Access focus history via REST API:
```
GET /cases/{case_id}/focus-history
```

Returns:
```json
{
  "case_id": "uuid-here",
  "case_number": "60CV-25-12762",
  "case_name": "Case Name",
  "entries": [
    {
      "timestamp": "2025-10-24T00:51:00.000000Z",
      "focus_text": "Scheduling depositions with expert witnesses",
      "actor": "user"
    },
    ...
  ],
  "generated_at": "2025-10-24T00:52:00Z"
}
```

## File Structure

Focus logs are stored in:
```
data/
  focus_logs/
    {case-id-1}.json
    {case-id-2}.json
    ...
```

Each log file contains:
```json
{
  "case_id": "uuid",
  "case_number": "case-number",
  "entries": [
    {
      "timestamp": "ISO-8601-timestamp",
      "focus_text": "The focus text",
      "actor": "user"
    }
  ]
}
```

## Benefits

1. **Complete Audit Trail**: Never lose track of what you were working on
2. **Historical Context**: Review past priorities and work patterns
3. **Case Management**: Easily see how a case has progressed
4. **Team Collaboration**: Track who updated focus and when
5. **Accessible Logs**: Simple JSON format that can be easily queried or backed up

## Configuration

Focus logs are excluded from version control via `.gitignore` to keep the repository clean while preserving logs locally.

## Technical Details

### Components

- **FocusLogManager** (`caseboard/focus_log.py`): Core logging functionality
- **CaseDataStore** (`caseboard/data_store.py`): Integration with save/audit system
- **FocusHistoryScreen** (`caseboard/screens.py`): Terminal UI viewer
- **Web API** (`web/main.py`): REST endpoint for web access

### Integration Points

Focus logging is automatically triggered when:
- A new case is created with initial focus text
- The `current_task` field is modified via the terminal UI
- Cases are saved via the data store

The feature integrates seamlessly with the existing audit logging system.
