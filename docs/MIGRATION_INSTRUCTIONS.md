# Messaging System Migration Instructions

## Database Migrations Required

The messaging system has been refactored with new models. You need to run migrations to update the database schema.

### Prerequisites

1. Activate your virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Run Migrations

```bash
# Create migrations for the new model structure
python manage.py makemigrations messaging

# Apply migrations
python manage.py migrate
```

### Migration Notes

The new model structure includes:
- **Conversation**: Simplified with `type` field (direct/group)
- **ConversationMember**: New model for tracking participants and read state
- **Message**: Simplified (removed recipient, group, attachments fields)
- **MessageRead**: New per-user read receipt model
- **MessageReaction**: Updated field name from `reaction` to `emoji`

### Data Migration Warning

If you have existing data in the messaging tables, you will need to create a data migration to:
1. Convert existing `Conversation.participants` ManyToMany to `ConversationMember` records
2. Migrate existing `Message.read_at` to `MessageRead` records
3. Update `MessageReaction.reaction` field to `emoji`

This is a breaking change for existing data.
