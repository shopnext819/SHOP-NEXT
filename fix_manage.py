import re

with open('shop/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace manage_seller_action completely
new_func = """@csrf_exempt
def manage_seller_action(request):
    if request.method == "POST" and request.session.get('admin_logged_in', False):
        try:
            import shutil
            import os
            import re
            from django.http import JsonResponse
            store_code = request.POST.get("store_code")
            action = request.POST.get("action")  # 'activate', 'deactivate', 'delete'
            
            # Check DB record First
            seller = SellerAccount.objects.filter(store_code=store_code).first()
            if seller:
                if action == "activate":
                    seller.is_approved = True
                    seller.save()
                elif action == "deactivate":
                    seller.is_approved = False
                    seller.save()
                elif action == "delete":
                    seller.delete()
                    
            # Check legacy text files
            found_legacy = False
            if os.path.exists(ROOT_DB_FOLDER):
                for d in os.listdir(ROOT_DB_FOLDER):
                    folder_path = os.path.join(ROOT_DB_FOLDER, d)
                    if os.path.isdir(folder_path) and d != "s":
                        txt_file = os.path.join(folder_path, f"seller_{d}.txt")
                        if os.path.exists(txt_file):
                            with open(txt_file, "r", encoding="utf-8") as f:
                                txt_content = f.read()
                            if f"Store Code: {store_code}" in txt_content:
                                found_legacy = True
                                if action == "delete":
                                    shutil.rmtree(folder_path, ignore_errors=True)
                                elif action == "deactivate":
                                    if "Status:" in txt_content:
                                        txt_content = re.sub(r'Status:.*', 'Status: Deactivated', txt_content)
                                    else:
                                        txt_content += "\\nStatus: Deactivated"
                                    with open(txt_file, "w", encoding="utf-8") as f: f.write(txt_content)
                                elif action == "activate":
                                    if "Status:" in txt_content:
                                        txt_content = re.sub(r'Status:.*', 'Status: Active', txt_content)
                                    else:
                                        txt_content += "\\nStatus: Active"
                                    with open(txt_file, "w", encoding="utf-8") as f: f.write(txt_content)
                                break
                                
            if seller or found_legacy:
                return JsonResponse({"status": "success", "message": f"Seller {action}d successfully"})
            else:
                return JsonResponse({"status": "error", "message": "Seller not found"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
            
    return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)"""

# Regex to find manage_seller_action
pattern = r'@csrf_exempt\ndef manage_seller_action\(request\):.*?return JsonResponse\(\{"status": "error", "message": "Unauthorized"\}, status=403\)'

content = re.sub(pattern, new_func, content, flags=re.DOTALL)

with open('shop/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated views.py")
