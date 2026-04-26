# Generated to recover lost follow relationships from M2M table

from django.db import migrations


def migrate_follow_relationships(apps, schema_editor):
    """
    Migrate follow relationships from the old User.following M2M field
    to the new Follow model. This attempts to recover data lost in migration 0005.
    """
    User = apps.get_model('users', 'User')
    Follow = apps.get_model('users', 'Follow')
    
    # Check if the old M2M table still exists in the database
    connection = schema_editor.connection
    cursor = connection.cursor()
    
    # Try to check if the old M2M table exists
    try:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE '%user_following%'
        """)
        tables = cursor.fetchall()
        
        if not tables:
            print("No user_following table found - data cannot be recovered")
            return
        
        # If table exists, migrate the data
        for table_info in tables:
            table_name = table_info[0]
            print(f"Found table: {table_name}")
            
            # Read data from the old M2M table
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            # The M2M table typically has: user_id, following_id (or similar)
            # Create Follow objects from this data
            for row in rows:
                try:
                    # Adjust column names based on actual table structure
                    user_id = row[0]
                    following_id = row[1]
                    
                    if user_id != following_id:  # Don't follow self
                        Follow.objects.get_or_create(
                            follower_id=user_id,
                            followed_id=following_id
                        )
                except Exception as e:
                    print(f"Error migrating row {row}: {e}")
                    
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        cursor.close()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_remove_user_following'),
    ]

    operations = [
        migrations.RunPython(migrate_follow_relationships, migrations.RunPython.noop),
    ]
