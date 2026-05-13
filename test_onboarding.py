#!/usr/bin/env python3
"""Simple test to verify onboarding implementation can be imported"""
import sys
import os

# Add the pwaninet directory to the Python path
sys.path.insert(0, '/home/zayne/projects/pwaninet')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')

import django
django.setup()

try:
    # Test importing models
    from users.models import User
    from groups.models import Group, Membership
    
    print("✓ Models imported successfully")
    
    # Test importing service
    from groups.services.academic_group_service import enroll_user_in_academic_groups
    
    print("✓ Academic group service imported successfully")
    
    # Check if new fields exist
    user_fields = [f.name for f in User._meta.get_fields()]
    group_fields = [f.name for f in Group._meta.get_fields()]
    
    print("✓ User model fields:", len(user_fields))
    print("✓ Group model fields:", len(group_fields))
    
    if 'has_completed_onboarding' in user_fields:
        print("✓ has_completed_onboarding field exists in User model")
    else:
        print("✗ has_completed_onboarding field missing from User model")
    
    if 'auto_join_on_signup' in group_fields:
        print("✓ auto_join_on_signup field exists in Group model")
    else:
        print("✗ auto_join_on_signup field missing from Group model")
    
    print("\n✓ All imports successful!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
