
import psycopg2

try:
    conn = psycopg2.connect("dbname='Munir' user='openpg' password='openpgpwd' host='localhost'")
    cur = conn.cursor()
    
    print("Searching for duplicate/stale views...")
    
    models = [
        'mysdb.order', 'mysdb.order.detail', 'mysdb.product', 'mysdb.store', 
        'mysdb.section', 'mysdb.project', 'mysdb.marketing_channel', 
        'mysdb.marketing_account', 'mysdb.product_relation', 
        'mysdb.product_marketing_relation', 'mysdb.period_target_cost',
        'mysdb.data.audit', 'mysdb.order.report'
    ]
    
    for model in models:
        cur.execute("""
            SELECT v.id, v.name, v.priority, d.name as xml_id
            FROM ir_ui_view v
            LEFT JOIN ir_model_data d ON (d.res_id = v.id AND d.model = 'ir.ui.view')
            WHERE v.model = %s
            ORDER BY v.priority ASC
        """, (model,))
        views = cur.fetchall()
        if views:
            print(f"\nModel {model} has {len(views)} views:")
            for v in views:
                print(f"  - ID: {v[0]}, Name: {v[1]}, Priority: {v[2]}, XML_ID: {v[3]}")
                # If XML_ID is None AND priority is not 1, it's likely a ghost
                if not v[3]:
                    print(f"    !!! DELETING ghost view {v[0]}")
                    cur.execute("DELETE FROM ir_ui_view WHERE id = %s", (v[0],))
        else:
            print(f"Model {model} has NO views in DB!")

    conn.commit()
    cur.close()
    conn.close()
    print("\nCleanup finished.")
except Exception as e:
    print(f"Error: {e}")

