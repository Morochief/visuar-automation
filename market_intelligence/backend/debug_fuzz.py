import sqlite3
from thefuzz import fuzz
import json

def test():
    conn = sqlite3.connect('market_intel.db')
    c = conn.cursor()
    
    # Load Visuar Products (they are the canonical ones)
    c.execute("SELECT id, name FROM products")
    visuar_products = c.fetchall()
    
    # Load Bristol Prices (to see what was matched)
    c.execute("SELECT id FROM competitors WHERE name='Bristol'")
    row = c.fetchone()
    if row:
        b_id = row[0]
        c.execute("SELECT product_id FROM price_logs WHERE competitor_id=?", (b_id,))
        print(f"Total explicit matches for Bristol: {len(c.fetchall())}")
    
    # Let's see the Visuar Names
    v_names = [r[1] for r in visuar_products if '12000' in r[1] or '18000' in r[1]]
    print(f"\nSample Visuar ACs: {v_names[:5]}")

if __name__ == '__main__':
    test()
