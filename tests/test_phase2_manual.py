import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.inventory_service import (
    get_all_products, get_stock, list_low_stock, list_out_of_stock,
    inventory_summary, update_stock, adjust_stock, search_products,
)
from src.tools.inventory_tools import (
    tool_get_stock, tool_list_low_stock, tool_inventory_summary,
    tool_search_products,
)

print("=== MANUAL PHASE 2 TEST ===\n")

# 1. Get all
all_prods = get_all_products()
print(f"1. All products: {len(all_prods)}")
assert len(all_prods) == 100, "Expected 100 products"

# 2. Inventory summary
sum_ = inventory_summary()
print(f"2. Summary: {sum_}")
assert sum_["total_products"] == 100

# 3. Low stock
low = list_low_stock()
print(f"3. Low stock count: {len(low)}")
for p in low[:3]:
    print(f"   - {p['name']} ({p['sku']}): {p['current_stock']} units (min {p['min_stock_threshold']})")

# 4. Out of stock
out_ = list_out_of_stock()
print(f"4. Out of stock count: {len(out_)}")
for p in out_[:3]:
    print(f"   - {p['name']} ({p['sku']}): 0 units")

# 5. Get single product by SKU
p = get_all_products()[0]
stock = get_stock(p["product_id"])
print(f"5. Get stock for {p['sku']}: {stock['current_stock']} units")

# 6. Update stock (then restore)
orig = stock["current_stock"]
update_stock(p["product_id"], orig + 5)
new_stock = get_stock(p["product_id"])
print(f"6. Update stock: {orig} -> {new_stock['current_stock']} (then restore)")
update_stock(p["product_id"], orig)

# 7. Adjust stock (positive)
adjust_stock(p["product_id"], 3)
print(f"7. Adjust +3: {get_stock(p['product_id'])['current_stock']} (restoring...)")
update_stock(p["product_id"], orig)

# 8. Tools
print(f"8. Tool low stock: {len(tool_list_low_stock())}")
print(f"8. Tool summary: {tool_inventory_summary()['low_stock_count']} low")

# 9. Search
search_res = search_products("Premium")
print(f"9. Search 'Premium': {len(search_res)} results")

print("\n=== ALL MANUAL CHECKS PASSED ===")
