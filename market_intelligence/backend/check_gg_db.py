import sqlite3
import pprint

def verify():
    conn = sqlite3.connect('market_intel.db')
    c = conn.cursor()
    c.execute("SELECT id FROM competitors WHERE name='Gonzalez Gimenez'")
    row = c.fetchone()
    if not row:
        print("Competitor 'Gonzalez Gimenez' not found!")
        return
    gg_id = row[0]
    
    c.execute("SELECT COUNT(*) FROM price_logs WHERE competitor_id=?", (gg_id,))
    count = c.fetchone()[0]
    print(f"Total Price Logs for Gonzalez Gimenez: {count}")
    
    c.execute("""
        SELECT p.name, pl.price 
        FROM price_logs pl 
        JOIN products p ON pl.product_id = p.id 
        WHERE pl.competitor_id=? 
        LIMIT 10
    """, (gg_id,))
    
    rows = c.fetchall()
    print("Sample Mappings:")
    for r in rows:
        print(f"Product: {r[0]} | GG Price: {r[1]}")

if __name__ == '__main__':
    verify()
