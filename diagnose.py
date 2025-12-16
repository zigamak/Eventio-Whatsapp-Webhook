#!/usr/bin/env python3
"""
Diagnostic script to verify all WhatsApp integration configurations
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_env_vars():
    """Check if all required environment variables are set"""
    print_section("ENVIRONMENT VARIABLES CHECK")
    
    required_vars = {
        'EVENTIO_ACCESS_TOKEN': 'Eventio Access Token',
        'PACKAGE_ACCESS_TOKEN': 'Package Access Token',
        'ACCOUNT2_ACCESS_TOKEN': 'IgnitioHub Access Token',
        'ACCOUNT1_PHONE_ID_EVENTIO': 'Eventio Phone ID',
        'ACCOUNT1_PHONE_ID_PACKAGE': 'Package Phone ID',
        'ACCOUNT2_PHONE_ID': 'IgnitioHub Phone ID',
        'DB_HOST': 'Database Host',
        'DB_NAME': 'Database Name',
        'DB_USER': 'Database User',
        'DB_PASSWORD': 'Database Password',
        'VERIFY_TOKEN': 'Webhook Verify Token'
    }
    
    all_present = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Hide sensitive data
            if 'TOKEN' in var or 'PASSWORD' in var:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"✅ {description:30} {display_value}")
        else:
            print(f"❌ {description:30} NOT SET")
            all_present = False
    
    if all_present:
        print("\n✅ All environment variables are set!")
    else:
        print("\n❌ Some environment variables are missing!")
    
    return all_present

def check_database():
    """Check database connection"""
    print_section("DATABASE CONNECTION CHECK")
    
    try:
        conn_string = (
            f"host={os.getenv('DB_HOST')} "
            f"port={os.getenv('DB_PORT', '5432')} "
            f"dbname={os.getenv('DB_NAME')} "
            f"user={os.getenv('DB_USER')} "
            f"password={os.getenv('DB_PASSWORD')} "
            f"sslmode={os.getenv('DB_SSLMODE', 'require')} "
            f"channel_binding={os.getenv('DB_CHANNEL_BINDING', 'require')}"
        )
        
        print("🔌 Attempting to connect to database...")
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"📊 PostgreSQL Version: {version[:50]}...")
        
        # Check if tables exist
        tables = ['eventio_messages', 'package_with_sense_messages', 'ignitiohub_messages']
        for table in tables:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = '{table}'
                )
            """)
            exists = cursor.fetchone()[0]
            status = "✅" if exists else "❌"
            print(f"{status} Table 'public.{table}': {'EXISTS' if exists else 'NOT FOUND'}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_config():
    """Check config.py is properly loaded"""
    print_section("CONFIG MODULE CHECK")
    
    try:
        import config
        print(f"✅ config.py imported successfully")
        print(f"📱 EVENTIO Phone ID: {config.ACCOUNT1_PHONE_ID_EVENTIO}")
        print(f"📱 PACKAGE Phone ID: {config.ACCOUNT1_PHONE_ID_PACKAGE}")
        print(f"📱 IGNITIOHUB Phone ID: {config.ACCOUNT2_PHONE_ID}")
        print(f"🌐 API Version: {config.VERSION}")
        print(f"🔗 Webhook URL: {config.WEBHOOK_URL}")
        return True
    except Exception as e:
        print(f"❌ Error importing config: {e}")
        return False

def check_whatsapp_utils():
    """Check whatsapp_utils module"""
    print_section("WHATSAPP UTILS MODULE CHECK")
    
    try:
        from whatsapp_utils import (
            get_table_name, get_token_for_phone_id, 
            PHONE_ID_TO_TABLE, PHONE_ID_TO_TOKEN
        )
        print(f"✅ whatsapp_utils.py imported successfully")
        
        print(f"\n📋 Phone ID to Table Mapping:")
        for phone_id, table in PHONE_ID_TO_TABLE.items():
            print(f"   {phone_id} → {table}")
        
        print(f"\n🔑 Phone ID to Token Mapping:")
        for phone_id in PHONE_ID_TO_TOKEN.keys():
            token = PHONE_ID_TO_TOKEN[phone_id]
            print(f"   {phone_id} → {token[:10]}...")
        
        return True
    except Exception as e:
        print(f"❌ Error importing whatsapp_utils: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  WHATSAPP INTEGRATION DIAGNOSTIC TOOL")
    print("="*60)
    
    # Load environment variables
    load_dotenv()
    print("✅ .env file loaded")
    
    results = {
        'Environment Variables': check_env_vars(),
        'Database Connection': check_database(),
        'Config Module': check_config(),
        'WhatsApp Utils': check_whatsapp_utils()
    }
    
    print_section("DIAGNOSTIC SUMMARY")
    
    all_passed = True
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {check}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("="*60)
        print("\nYour configuration looks good. If you still can't send messages:")
        print("1. Run: python test_whatsapp_send.py")
        print("2. Check Flask logs when sending from the web interface")
        print("3. Check browser console (F12) for JavaScript errors")
        print("4. Verify recipient phone number format (e.g., 2348108831865)")
        return 0
    else:
        print("❌ SOME CHECKS FAILED!")
        print("="*60)
        print("\nPlease fix the issues above before testing message sending.")
        return 1

if __name__ == "__main__":
    sys.exit(main())