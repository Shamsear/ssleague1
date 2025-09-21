from app import app, db
from sqlalchemy import text

with app.app_context():
    # Get all sequences
    result = db.session.execute(text("SELECT sequence_name FROM information_schema.sequences"))
    sequences = [row[0] for row in result]
    print(f"Found {len(sequences)} sequences:")
    for seq in sequences:
        print(f"  - {seq}")
    
    # Get all tables with id columns that need fixing
    result = db.session.execute(text('''
        SELECT table_name
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND column_name = 'id' 
        AND data_type = 'integer'
        AND is_nullable = 'NO'
        AND column_default IS NULL
        ORDER BY table_name
    '''))
    
    tables_to_fix = [row[0] for row in result]
    print(f"\nTables to fix: {len(tables_to_fix)}")
    
    fixed_count = 0
    for table in tables_to_fix:
        # Try to find matching sequence
        expected_seq = f"{table}_id_seq"
        if expected_seq in sequences:
            try:
                sql = f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT nextval('{expected_seq}'::regclass)"
                db.session.execute(text(sql))
                print(f"✅ Fixed {table} -> {expected_seq}")
                fixed_count += 1
            except Exception as e:
                print(f"❌ Failed to fix {table}: {e}")
        else:
            print(f"⚠️  No sequence found for {table} (expected: {expected_seq})")
    
    if fixed_count > 0:
        db.session.commit()
        print(f"\n✅ Successfully fixed {fixed_count} tables")
    else:
        print("\n⚠️  No tables were fixed")