import django  # type: ignore
import os
import datetime
import re
import base64
import json
import glob
from django.db.models import Q  # type: ignore
from django.shortcuts import render, redirect  # type: ignore
from django.http import JsonResponse  # type: ignore
from django.contrib import messages  # type: ignore
from django.contrib.auth.models import User  # type: ignore
from django.conf import settings  # type: ignore
from django.views.decorators.csrf import csrf_exempt  # type: ignore
from .models import SellerAccount, Product, Message, CallSignal, UserProfile
from django.contrib.auth.decorators import login_required
# Common Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DB_FOLDER = os.path.normpath(os.path.join(BASE_DIR, "templates", "database", "center"))
STATIC_IMAGES_DIR = os.path.join(settings.BASE_DIR, 'static', 'images')

# =========================
# HELPER: Get All Products (Database Only)
# =========================
def get_all_products():
    all_prods = {}
    
    for p in Product.objects.filter(is_available=True, is_approved=True):
        image_name = p.image.name if p.image else "images/clock4.jpg"
        seller_loc = p.seller.city if p.seller else "N/A"
        all_prods[10000 + p.id] = {
            "name": p.name,
            "price": p.price,
            "image": image_name,
            "country": seller_loc
        }
    return all_prods

# =========================
# VIEWS
# =========================

def home(request):
    query = request.GET.get("q")
    sort_by = request.GET.get("sort", "relevant")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    
    current_products_dict = get_all_products()
    products_list = [{"id": k, **v} for k, v in current_products_dict.items()]

    if query:
        products_list = [p for p in products_list if query.lower() in p["name"].lower()]

    if min_price and min_price.isdigit():
        products_list = [p for p in products_list if int(p["price"]) >= int(min_price)]
    if max_price and max_price.isdigit():
        products_list = [p for p in products_list if int(p["price"]) <= int(max_price)]

    if sort_by == "low":
        products_list.sort(key=lambda x: int(x["price"]))
    elif sort_by == "high":
        products_list.sort(key=lambda x: int(x["price"]), reverse=True)
    elif sort_by == "new":
        products_list.sort(key=lambda x: x["id"], reverse=True)

    chats = get_user_chats(request.user) if request.user.is_authenticated else []
    return render(request, "home.html", {
        "products": products_list,
        "query": query,
        "current_sort": sort_by,
        "chats": chats
    })

def product_detail(request, product_id):
    real_id = product_id - 10000 if product_id > 10000 else product_id
    product = Product.objects.filter(id=real_id).first()
    
    if not product:
        return redirect('home')
        
    images = []
    # Order: Video (if exists) -> image (front) -> image2-6
    if product.video:
        images.append({"type": "video", "url": "/static/" + product.video.name})
    
    if product.image:
        images.append({"type": "image", "url": "/static/" + product.image.name})
    if product.image2:
        images.append({"type": "image", "url": "/static/" + product.image2.name})
    if product.image3:
        images.append({"type": "image", "url": "/static/" + product.image3.name})
    if product.image4:
        images.append({"type": "image", "url": "/static/" + product.image4.name})
    if product.image5:
        images.append({"type": "image", "url": "/static/" + product.image5.name})
    if product.image6:
        images.append({"type": "image", "url": "/static/" + product.image6.name})
        
    return render(request, "product_detail.html", {
        "product": product,
        "p_id": product_id,
        "images": images
    })

def add_to_cart(request, product_id):
    cart = request.session.get("cart", [])
    current_products_dict = get_all_products()

    if product_id in cart:
        messages.warning(request, "This item is already in the cart.")
        return redirect("home")

    if product_id in current_products_dict:
        cart.append(product_id)
        request.session["cart"] = cart
        messages.success(request, "Item added to cart successfully.")

    return redirect("home")

def cart(request):
    cart_ids = request.session.get("cart", [])
    current_products_dict = get_all_products()

    cart_items = []
    for raw_pid in cart_ids:
        try:
            pid = int(raw_pid)
            if pid in current_products_dict:
                cart_items.append(current_products_dict[pid])
        except (ValueError, TypeError):
            pass

    total = sum(item["price"] for item in cart_items)

    return render(request, "cart.html", {
        "cart": cart_items,
        "total": total
    })

def remove_from_cart(request, index):
    cart = request.session.get("cart", [])
    if 0 <= index < len(cart):
        cart.pop(index)
        request.session["cart"] = cart
    return redirect("cart")
from .models import SellerAccount

def get_user_chats(user):
    if not user.is_authenticated:
        return []
    msgs = Message.objects.filter(
        Q(sender=user) | Q(receiver=user)
    ).order_by("-timestamp")
    users = {}
    for m in msgs:
        other = m.receiver if m.sender == user else m.sender
        key = f"{other.username}_{m.product_id}"
        
        if key not in users:
            display_name = other.username
            acc = SellerAccount.objects.filter(user=other).first()
            if acc:
                display_name = f"{acc.store_name} (Store)"
            
            users[key] = {
                "user": other.username,
                "display_name": display_name,
                "product": m.product_id,
                "last": m.text or "📷 Media Message",
                "time": m.timestamp.strftime("%I:%M %p"),
                "unread": not m.seen and m.receiver == user
            }
    return users.values()

def chat(request, username, product_id):
    if not request.user.is_authenticated:
        if not request.session.session_key:
            request.session.create()
        guest_username = f"guest_{request.session.session_key[:10]}"
        user, _ = User.objects.get_or_create(username=guest_username)
        from django.contrib.auth import login  # type: ignore
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
    # Get the display name of the 'other' user for the header
    other_display_name = username
    from .models import SellerAccount, Product
    other_user_obj = User.objects.filter(username=username).first()
    if other_user_obj:
        acc = SellerAccount.objects.filter(user=other_user_obj).first()
        if acc:
            other_display_name = acc.store_name

    product_obj = None
    try:
        if product_id != "0":
            product_obj = Product.objects.get(id=int(product_id))
    except:
        pass

    chats = get_user_chats(request.user)
    return render(request, "chat.html", {
        "other": username,
        "other_display_name": other_display_name,
        "product_id": product_id,
        "product": product_obj,
        "me": request.user.username,
        "chats": chats
    })

def inbox(request):
    chats = get_user_chats(request.user)
    return render(request, "inbox.html", {"chats": chats})

# ==========================================
# WEBRTC NATIVE SIGNALING VIEWS
# ==========================================

from .models import BlockedUser, Complaint

def report_user(request, username):
    if request.method == "POST":
        reason = request.POST.get("reason", "Inappropriate behavior reported from chat.")
        Complaint.objects.create(
            sender=request.user,
            reported_user=username,
            body=f"Report against {username}: {reason}"
        )
        return JsonResponse({"status": "reported"})
    return JsonResponse({"status": "error"}, status=400)

def block_user(request, username):
    try:
        user_to_block = User.objects.get(username=username)
        BlockedUser.objects.get_or_create(
            user=request.user,
            blocked=user_to_block
        )
        return JsonResponse({"status":"blocked"})
    except User.DoesNotExist:
        return JsonResponse({"status":"error", "message":"User not found"}, status=404)
# ==========================================
@csrf_exempt
def send_signal(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            callee = data.get("callee")
            signal_type = data.get("type")
            payload = data.get("payload")
            
            store_name = request.COOKIES.get("store_name", "Unknown Store")
            caller = store_name if store_name != "Unknown Store" else "Buyer"
            
            if callee and signal_type and payload is not None:
                CallSignal.objects.create(
                    caller=caller,
                    callee=callee,
                    signal_type=signal_type,
                    payload=json.dumps(payload)
                )
                return JsonResponse({"status": "success"})
            return JsonResponse({"status": "error", "message": "Missing fields"}, status=400)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

@csrf_exempt
def poll_signals(request):
    if request.method == "GET":
        other_party = request.GET.get("user")
        if not other_party:
            return JsonResponse({"status": "error", "message": "Missing user"}, status=400)
            
        store_name = request.COOKIES.get("store_name", "Unknown Store")
        my_name = store_name if store_name != "Unknown Store" else "Buyer"
        
        # Get unread signals sent TO me, FROM the other party
        signals = CallSignal.objects.filter(callee=my_name, caller=other_party, is_read=False).order_by("created_at")
        
        results = []
        for sig in signals:
            results.append({
                "id": sig.id,
                "type": sig.signal_type,
                "payload": json.loads(sig.payload),
                "caller": sig.caller
            })
            sig.is_read = True
            sig.save()
            
        return JsonResponse({"status": "success", "signals": results})
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

def chats_list(request):
    # This view will show the clean list of chats a seller or user has
    chat_history = request.session.get("chat_history", {})
    
    # We will format this dictionary back to the template
    # Also add some dummy ones just so it doesn't look empty for the demo
    demo_users = ["Ali", "Zain"]
    
    formatted_chats = []
    
    # Add real chat history
    for seller, msgs in chat_history.items():
        if seller in demo_users:
            demo_users.remove(seller)
            
        last_msg = msgs[-1] if msgs else {"text": "No messages yet...", "time": ""}
        formatted_chats.append({
            "name": seller,
            "last_message": last_msg["text"],
            "time": last_msg["time"]
        })
        
    # Add dummies
    for u in demo_users:
        formatted_chats.append({
            "name": u,
            "last_message": "Can I get a discount?",
            "time": "1h ago"
        })
        
    # User's own store name context
    store_name = request.COOKIES.get("store_name", "")
    if not store_name and request.user.is_authenticated:
        store_name = request.user.username
        
    return render(request, "chats_list.html", {
        "chats": formatted_chats,
        "store_name": store_name
    })

def seller_login(request):
    if request.method == "POST":
        s_name = request.POST.get("store_name", "").strip()
        s_code = request.POST.get("store_code", "").strip()

        if s_name.lower() == "shop next":
            if s_code != "1122":
                return render(request, "seller_login.html", {"error": "Incorrect Store Name or Code!"})
            s_name = "SHOP NEXT" # Normalize case
            user, _ = User.objects.get_or_create(username="seller_1122")
            account, _ = SellerAccount.objects.get_or_create(user=user, store_name=s_name, defaults={'store_code': s_code})
            
            from django.contrib.auth import login
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            response = redirect("seller_dashboard_home")
            response.set_cookie("store_name", s_name, max_age=86400)
            return response

        try:
            account = SellerAccount.objects.filter(store_name=s_name, store_code=s_code).first()
            if account:
                from django.contrib.auth import login
                login(request, account.user, backend='django.contrib.auth.backends.ModelBackend')
                response = redirect("seller_dashboard_home")
                response.set_cookie("store_name", account.store_name, max_age=86400)
                return response
        except Exception:
            account = None

        if not account:
            safe_name = s_name.replace(" ", "_").replace("/", "_")
            text_file = os.path.join(ROOT_DB_FOLDER, safe_name, f"seller_{safe_name}.txt")
            if os.path.exists(text_file):
                with open(text_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if f"Store Code: {s_code}" in content:
                    user, _ = User.objects.get_or_create(username=f"seller_{s_code}")
                    SellerAccount.objects.get_or_create(user=user, store_name=s_name, store_code=s_code)
                    
                    from django.contrib.auth import login
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    
                    response = redirect("seller_dashboard_home")
                    response.set_cookie("store_name", s_name, max_age=86400)
                    return response
                    
        return render(request, "seller_login.html", {"error": "Incorrect Store Name or Code!"})
    return render(request, "seller_login.html")

def seller_dashboard_home(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_product":
            store_name = request.COOKIES.get("store_name", "")
            seller = None
            
            if request.user.is_authenticated:
                seller = SellerAccount.objects.filter(user=request.user).first()
            
            if not seller and store_name:
                seller = SellerAccount.objects.filter(store_name=store_name).first()
                if not seller:
                    user, _ = User.objects.get_or_create(username=f"legacy_{store_name.replace(' ', '_')}")
                    seller, _ = SellerAccount.objects.get_or_create(user=user, store_name=store_name, defaults={'store_code': f"legacy_{user.id}"})
                
            if not seller:
                return JsonResponse({'status': 'error', 'message': 'Seller session expired. Please log in again.'})
            try:
                name = request.POST.get("product_name")
                desc = request.POST.get("product_desc")
                brand = request.POST.get("brand_name")
                if brand in ['no_brand', '', None]:
                    brand = request.POST.get("brand_manual") or "No Brand"
                
                try:
                    price = int(request.POST.get("price", 0))
                except:
                    price = 0
                try:
                    stock = int(request.POST.get("stock", 0))
                except:
                    stock = 0
                    
                # Warranty Handling
                warranty_type = request.POST.get("warranty_type", "No Warranty")
                warranty_policy = request.POST.get("warranty_policy", "None") if warranty_type == "In Warranty" else "None"

                # Handle Multiple Images & Video
                import uuid
                unique_dir = f"p_{uuid.uuid4().hex[:8]}"
                file_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'uploads', unique_dir)
                os.makedirs(file_dir, exist_ok=True)

                def save_file(file_obj, sub_folder=""):
                    if not file_obj: return None
                    target_dir = os.path.join(file_dir, sub_folder)
                    os.makedirs(target_dir, exist_ok=True)
                    file_path = os.path.join(target_dir, file_obj.name)
                    with open(file_path, 'wb+') as destination:
                        for chunk in file_obj.chunks():
                            destination.write(chunk)
                    return f"images/uploads/{unique_dir}/{sub_folder}{file_obj.name}"

                prd = Product(
                    name=name,
                    price=price,
                    description=desc,
                    brand=brand,
                    category=seller.category,
                    stock=stock,
                    is_available=True,
                    is_approved=False,
                    seller=seller,
                    warranty_policy=warranty_policy
                )

                prd.image.name = save_file(request.FILES.get("product_image"))
                prd.image2.name = save_file(request.FILES.get("image2"))
                prd.image3.name = save_file(request.FILES.get("image3"))
                prd.image4.name = save_file(request.FILES.get("image4"))
                prd.image5.name = save_file(request.FILES.get("image5"))
                prd.image6.name = save_file(request.FILES.get("image6"))
                prd.video.name = save_file(request.FILES.get("product_video"), "videos/")
                
                prd.save()
                return JsonResponse({'status': 'success'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
        elif action == "update_product":
            try:
                p_id = request.POST.get("pid")
                p = Product.objects.get(id=p_id)
                p.name = request.POST.get("product_name", p.name) or p.name
                p.description = request.POST.get("product_desc", p.description) or p.description
                
                price_val = request.POST.get("price")
                if price_val:
                    try: p.price = int(price_val)
                    except: pass
                    
                stock_val = request.POST.get("stock")
                if stock_val:
                    try: p.stock = int(stock_val)
                    except: pass
                    
                brand_val = request.POST.get("brand_name")
                if brand_val:
                    p.brand = brand_val
                    if brand_val == 'no_brand' or brand_val == '':
                        p.brand = request.POST.get("brand_manual", "No Brand")
                
                # Warranty Handling
                warranty_type = request.POST.get("warranty_type")
                if warranty_type:
                    if warranty_type == "In Warranty":
                        p.warranty_policy = request.POST.get("warranty_policy", "None")
                    else:
                        p.warranty_policy = "None"

                # Handle Multiple Images & Video
                import uuid
                unique_dir = f"p_{uuid.uuid4().hex[:8]}"
                file_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'uploads', unique_dir)
                os.makedirs(file_dir, exist_ok=True)

                def save_file(file_obj, sub_folder=""):
                    if not file_obj: return None
                    target_dir = os.path.join(file_dir, sub_folder)
                    os.makedirs(target_dir, exist_ok=True)
                    file_path = os.path.join(target_dir, file_obj.name)
                    with open(file_path, 'wb+') as destination:
                        for chunk in file_obj.chunks():
                            destination.write(chunk)
                    return f"images/uploads/{unique_dir}/{sub_folder}{file_obj.name}"

                # Only update if a new file is provided
                img1 = save_file(request.FILES.get("product_image"))
                if img1: p.image.name = img1
                
                img2 = save_file(request.FILES.get("image2"))
                if img2: p.image2.name = img2
                
                img3 = save_file(request.FILES.get("image3"))
                if img3: p.image3.name = img3
                
                img4 = save_file(request.FILES.get("image4"))
                if img4: p.image4.name = img4
                
                img5 = save_file(request.FILES.get("image5"))
                if img5: p.image5.name = img5
                
                img6 = save_file(request.FILES.get("image6"))
                if img6: p.image6.name = img6
                
                vid = save_file(request.FILES.get("product_video"), "videos/")
                if vid: p.video.name = vid

                p.save()
                return JsonResponse({'status': 'success'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})

    # Initial context values
    banner_data = profile_data = None
    seller_email = seller_phone = seller_password = ""
    seller_products = []

    # 1. Start with cookie value
    store_name = request.COOKIES.get("store_name", "Your Store Name")
    
    # 2. Resolve store_name from directories if not in cookie
    if (not store_name or store_name == "Your Store Name") and os.path.exists(ROOT_DB_FOLDER):
        dirs = [d for d in os.listdir(ROOT_DB_FOLDER) if os.path.isdir(os.path.join(ROOT_DB_FOLDER, d)) and d != "s"]
        if dirs:
            dirs.sort(key=lambda x: os.path.getmtime(os.path.join(ROOT_DB_FOLDER, x)), reverse=True)
            safe_dir = dirs[0]
            # Try to get the actual store_name from the text file
            txt_file = os.path.join(ROOT_DB_FOLDER, safe_dir, f"seller_{safe_dir}.txt")
            if os.path.exists(txt_file):
                with open(txt_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("Store Name:"):
                            store_name = line.split("Store Name:")[1].strip()
                            break
            # Fallback if parsing fails
            if not store_name or store_name == "Your Store Name":
                store_name = safe_dir

    seller_obj = None
    # 3. Priority: Logged in Django User
    if request.user.is_authenticated:
        seller_obj = SellerAccount.objects.filter(user=request.user).first()
    
    # 4. Fallback: Lookup by store_name
    if not seller_obj and store_name and store_name != "Your Store Name":
        seller_obj = SellerAccount.objects.filter(store_name=store_name).first()

    # 5. If seller_obj found, populate data from DB
    if seller_obj:
        store_name = seller_obj.store_name
        seller_email = seller_obj.email or ""
        seller_phone = seller_obj.phone or ""
        seller_products = Product.objects.filter(seller=seller_obj).order_by('-id')

    # Prepare file path for backups
    safe_name = store_name.replace(" ", "_").replace("/", "_") if store_name else "default"
    seller_folder = os.path.normpath(os.path.join(ROOT_DB_FOLDER, safe_name))

    if os.path.exists(seller_folder) and store_name and store_name != "Your Store Name":
        text_db_file = os.path.join(seller_folder, f"seller_{safe_name}.txt")
        if os.path.exists(text_db_file):
            with open(text_db_file, "r", encoding="utf-8") as file:
                for line in file:
                    if line.startswith("Email:"): seller_email = line.split("Email:")[1].strip()
                    elif line.startswith("Phone:"): seller_phone = line.split("Phone:")[1].strip()
                    elif line.startswith("Store Code:"): seller_password = line.split("Store Code:")[1].strip()
                    elif line.startswith("Store Name:"): 
                        # Only overwrite if the file has a non-empty name and we don't have one from DB
                        f_name = line.split("Store Name:")[1].strip()
                        if f_name and (not seller_obj):
                            store_name = f_name

        banner_files = glob.glob(os.path.join(seller_folder, "banner.*"))
        if banner_files:
            try:
                with open(banner_files[0], "rb") as f:
                    ext = banner_files[0].split('.')[-1]
                    banner_data = f"data:image/{ext};base64," + base64.b64encode(f.read()).decode()
            except: pass
                
        profile_files = glob.glob(os.path.join(seller_folder, "profile.*"))
        if profile_files:
            try:
                with open(profile_files[0], "rb") as f:
                    ext = profile_files[0].split('.')[-1]
                    profile_data = f"data:image/{ext};base64," + base64.b64encode(f.read()).decode()
            except: pass

    store_complaints = []
    if seller_obj:
        store_complaints = Complaint.objects.filter(
            Q(reported_user=seller_obj.store_name) | 
            Q(reported_user=seller_obj.store_code) |
            Q(reported_user=seller_obj.user.username)
        ).order_by('-id')
    elif store_name and store_name != "Your Store Name":
        store_complaints = Complaint.objects.filter(reported_user=store_name).order_by('-id')

    seller_chats = get_user_chats(request.user) if request.user.is_authenticated else []
    me_username = request.user.username if request.user.is_authenticated else ""

    return render(request, "seller_dashboard_home.html", {
        "store_name": store_name,
        "banner_data": banner_data,
        "profile_data": profile_data,
        "seller_email": seller_email,
        "seller_phone": seller_phone,
        "seller_password": seller_password,
        "seller_products": seller_products,
        "seller_obj": seller_obj,
        "store_complaints": store_complaints,
        "chats": seller_chats,
        "me": me_username,
    })

@csrf_exempt
def update_product(request):
    if request.method == "POST":
        p_id = request.POST.get("pid")
        try:
            p = Product.objects.get(id=p_id)
            p.name = request.POST.get("product_name", p.name) or p.name
            p.description = request.POST.get("product_desc", p.description) or p.description
            
            price_val = request.POST.get("price")
            if price_val:
                try: p.price = int(price_val)
                except: pass
                
            stock_val = request.POST.get("stock")
            if stock_val:
                try: p.stock = int(stock_val)
                except: pass
                
            # Handle brand and other updates if needed
            brand_val = request.POST.get("brand_name")
            if brand_val:
                p.brand = brand_val
                if brand_val == 'no_brand' or brand_val == '':
                    p.brand = request.POST.get("brand_manual", "No Brand")
            
            # Update Warranty
            warranty_type = request.POST.get("warranty_type")
            if warranty_type:
                if warranty_type == "In Warranty":
                    p.warranty_policy = request.POST.get("warranty_policy", "None")
                else:
                    p.warranty_policy = "None"
            
            # Handle Multiple Images & Video
            import uuid
            unique_dir = f"p_upd_{uuid.uuid4().hex[:8]}"
            file_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'uploads', unique_dir)
            os.makedirs(file_dir, exist_ok=True)

            def save_file(file_obj, sub_folder=""):
                if not file_obj: return None
                target_dir = os.path.join(file_dir, sub_folder)
                os.makedirs(target_dir, exist_ok=True)
                file_path = os.path.join(target_dir, file_obj.name)
                with open(file_path, 'wb+') as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)
                return f"images/uploads/{unique_dir}/{sub_folder}{file_obj.name}"

            img1 = save_file(request.FILES.get("product_image"))
            if img1: p.image.name = img1
            
            img2 = save_file(request.FILES.get("image2"))
            if img2: p.image2.name = img2
            
            img3 = save_file(request.FILES.get("image3"))
            if img3: p.image3.name = img3
            
            img4 = save_file(request.FILES.get("image4"))
            if img4: p.image4.name = img4
            
            img5 = save_file(request.FILES.get("image5"))
            if img5: p.image5.name = img5
            
            img6 = save_file(request.FILES.get("image6"))
            if img6: p.image6.name = img6
            
            vid = save_file(request.FILES.get("product_video"), "videos/")
            if vid: p.video.name = vid

            p.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})

@csrf_exempt
def delete_product(request):
    if request.method == "POST":
        p_id = request.POST.get("pid")
        store_name = request.COOKIES.get("store_name", "")
        try:
            seller = SellerAccount.objects.filter(store_name=store_name).first()
            if seller:
                Product.objects.filter(id=p_id, seller=seller).delete()
                return JsonResponse({"status": "success"})
            return JsonResponse({"status": "error", "message": "Seller not found"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})

def seller_center(request):
    return render(request, "seller center.html")

def seller_register(request):
    if request.method == "POST":
        store_name = request.POST.get("store_name", "Unknown Store")
        store_code = request.POST.get("store_code", "")
        store_desc = request.POST.get("store_desc", "")
        category = request.POST.get("category", "")
        email = request.POST.get("email", "")
        phone = request.POST.get("phone", "")
        address = request.POST.get("address", "")
        city = request.POST.get("city", "")
        zipcode = request.POST.get("zipcode", "")
        legal_name = request.POST.get("legal_name", "")
        dob = request.POST.get("dob", "")
        payment_type = request.POST.get("payment_type", "")
        
        dob_val = None
        if dob:
            try: dob_val = datetime.datetime.strptime(dob, "%Y-%m-%d").date()
            except: pass

        user = request.user if request.user.is_authenticated else User.objects.first()
        if not user:
            user = User.objects.create(username=f"seller_{store_code or phone}", email=email)

        try:
            SellerAccount.objects.create(
                user=user, store_name=store_name, store_code=store_code, store_desc=store_desc,
                category=category, address=address, city=city, zipcode=zipcode,
                email=email, phone=phone, legal_name=legal_name, dob=dob_val, payment_type=payment_type
            )
        except Exception as e:
            print("DB Write Error:", e)

        safe_name = store_name.replace(" ", "_").replace("/", "_")
        seller_folder = os.path.join(ROOT_DB_FOLDER, safe_name)
        if not os.path.exists(seller_folder): os.makedirs(seller_folder)
            
        banner_file = request.FILES.get('banner')
        profile_file = request.FILES.get('profile')
        
        if banner_file:
            ext = banner_file.name.split('.')[-1]
            with open(os.path.join(seller_folder, f"banner.{ext}"), "wb+") as b_dest:
                for chunk in banner_file.chunks(): b_dest.write(chunk)
                    
        if profile_file:
            ext = profile_file.name.split('.')[-1]
            with open(os.path.join(seller_folder, f"profile.{ext}"), "wb+") as p_dest:
                for chunk in profile_file.chunks(): p_dest.write(chunk)
                    
        file_path = os.path.join(seller_folder, f"seller_{safe_name}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Store Name: {store_name}\nStore Code: {store_code}\nDescription: {store_desc}\nEmail: {email}\nPhone: {phone}\n")

        response = redirect("seller_dashboard_home")
        response.set_cookie("store_name", store_name, max_age=86400)
        return response

    return render(request, "seller_register.html")

@csrf_exempt
def update_seller_settings(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action, value = data.get("action"), data.get("value")
        except:
            action, value = request.POST.get("action"), request.POST.get("value")
            
        store_name = request.COOKIES.get("store_name", "Your Store Name")
        
        # Resolve store_name if missing
        if (not store_name or store_name == "Your Store Name") and os.path.exists(ROOT_DB_FOLDER):
            dirs = [d for d in os.listdir(ROOT_DB_FOLDER) if os.path.isdir(os.path.join(ROOT_DB_FOLDER, d)) and d != "s"]
            if dirs:
                dirs.sort(key=lambda x: os.path.getmtime(os.path.join(ROOT_DB_FOLDER, x)), reverse=True)
                safe_dir = dirs[0]
                txt_file = os.path.join(ROOT_DB_FOLDER, safe_dir, f"seller_{safe_dir}.txt")
                if os.path.exists(txt_file):
                    with open(txt_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("Store Name:"):
                                store_name = line.split("Store Name:")[1].strip()
                                break
                if not store_name or store_name == "Your Store Name":
                    store_name = safe_dir

        acc = None
        if request.user.is_authenticated:
            acc = SellerAccount.objects.filter(user=request.user).first()
        
        if not acc and store_name and store_name != "Your Store Name":
            acc = SellerAccount.objects.filter(store_name=store_name).first()



        if acc:
            store_name = acc.store_name
            if action == "email": acc.email = value
            elif action == "phone": acc.phone = value
            elif action == "password": acc.store_code = value
            elif action == "address_update":
                acc.address = value.get("details", "")
                acc.city = value.get("city", "")
            elif action == "idbank_update":
                acc.legal_name = value.get("legal_name", "")
                acc.bank_name = value.get("bank_name", "")
                acc.account_no = value.get("account_no", "")
                acc.id_no = value.get("id_no", "")
                acc.tax_no = value.get("tax_no", "")
                acc.iban = value.get("iban", "")
                acc.bank_code = value.get("bank_code", "")
                acc.bank_branch = value.get("bank_branch", "")
                acc.business_address = value.get("business_address", "")
                acc.seller_type = value.get("seller_type", "personal")
            acc.save()
                    
        safe_name = store_name.replace(" ", "_").replace("/", "_")
        seller_folder = os.path.join(ROOT_DB_FOLDER, safe_name)
        text_db_file = os.path.join(seller_folder, f"seller_{safe_name}.txt")
        
        if os.path.exists(text_db_file):
            with open(text_db_file, "r", encoding="utf-8") as f: content = f.read()
            if action == "email": content = re.sub(r'Email:.*', f'Email: {value}', content)
            elif action == "phone": content = re.sub(r'Phone:.*', f'Phone: {value}', content)
            elif action == "password": content = re.sub(r'Store Code:.*', f'Store Code: {value}', content)
            with open(text_db_file, "w", encoding="utf-8") as f: f.write(content)
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=400)

def help_page(request): return render(request, "help.html")
def privacy_policy(request): return render(request, "privacy_policy.html")
@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, "profile.html", {"profile": user_profile})

@login_required
def complete_onboarding(request):
    if request.method == "POST":
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Capture data
        real_name = request.POST.get("real_name")
        phone = request.POST.get("phone")
        birthday = request.POST.get("birthday")
        location = request.POST.get("location") # We store this in 'source'
        
        if real_name:
            # Update first_name in User model if possible
            names = real_name.split(" ", 1)
            request.user.first_name = names[0]
            if len(names) > 1:
                request.user.last_name = names[1]
            request.user.save()
            
            # Also update in UserProfile if you want
            user_profile.first_name = names[0]
            if len(names) > 1:
                user_profile.last_name = names[1]

        if phone: user_profile.phone = phone
        if birthday: user_profile.birthday = birthday
        if location: user_profile.source = location # Saving location to source
        
        user_profile.is_completed = True
        user_profile.save()
        
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def store_settings(request):
    store_name = request.COOKIES.get("store_name", "Your Store Name")
    if (not store_name or store_name == "Your Store Name") and os.path.exists(ROOT_DB_FOLDER):
        dirs = [d for d in os.listdir(ROOT_DB_FOLDER) if os.path.isdir(os.path.join(ROOT_DB_FOLDER, d)) and d != "s"]
        if dirs:
            dirs.sort(key=lambda x: os.path.getmtime(os.path.join(ROOT_DB_FOLDER, x)), reverse=True)
            store_name = dirs[0]
            
    safe_name = store_name.replace(" ", "_").replace("/", "_")
    seller_folder = os.path.join(ROOT_DB_FOLDER, safe_name)
    text_db_file = os.path.join(seller_folder, f"seller_{safe_name}.txt")
    
    current_name, current_code, current_desc = store_name, "", ""
    if os.path.exists(text_db_file):
        with open(text_db_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Store Name:"): current_name = line.split("Store Name:")[1].strip()
                elif line.startswith("Store Code:"): current_code = line.split("Store Code:")[1].strip()
                elif line.startswith("Description:"): current_desc = line.split("Description:")[1].strip()
                    
    if request.method == "POST":
        new_name = request.POST.get("store_name", current_name).strip()
        new_code = request.POST.get("store_code", current_code).strip()
        new_desc = request.POST.get("store_desc", current_desc).strip()
        banner_file, profile_file = request.FILES.get("banner"), request.FILES.get("profile")
        
        new_safe_name = new_name.replace(" ", "_").replace("/", "_")
        new_seller_folder = os.path.join(ROOT_DB_FOLDER, new_safe_name)
        new_text_db_file = os.path.join(new_seller_folder, f"seller_{new_safe_name}.txt")
        
        if safe_name != new_safe_name and os.path.exists(seller_folder):
            os.rename(seller_folder, new_seller_folder)
            old_txt = os.path.join(new_seller_folder, f"seller_{safe_name}.txt")
            if os.path.exists(old_txt): os.rename(old_txt, new_text_db_file)
        elif not os.path.exists(new_seller_folder): os.makedirs(new_seller_folder)
            
        if os.path.exists(new_text_db_file):
            with open(new_text_db_file, "r", encoding="utf-8") as f: content = f.read()
            content = re.sub(r'Store Name:.*', f'Store Name: {new_name}', content)
            content = re.sub(r'Store Code:.*', f'Store Code: {new_code}', content)
            content = re.sub(r'Description:.*', f'Description: {new_desc}', content)
            with open(new_text_db_file, "w", encoding="utf-8") as f: f.write(content)
                
        if request.user.is_authenticated:
            acc = SellerAccount.objects.filter(user=request.user).first()
            if acc:
                acc.store_name, acc.store_code, acc.store_desc = new_name, new_code, new_desc
                acc.save()

        if banner_file:
            for old in glob.glob(os.path.join(new_seller_folder, "banner.*")): os.remove(old)
            ext = banner_file.name.split('.')[-1]
            with open(os.path.join(new_seller_folder, f"banner.{ext}"), "wb+") as d:
                for chunk in banner_file.chunks(): d.write(chunk)
                    
        if profile_file:
            for old in glob.glob(os.path.join(new_seller_folder, "profile.*")): os.remove(old)
            ext = profile_file.name.split('.')[-1]
            with open(os.path.join(new_seller_folder, f"profile.{ext}"), "wb+") as d:
                for chunk in profile_file.chunks(): d.write(chunk)
                    
        resp = redirect("seller_dashboard_home")
        resp.set_cookie("store_name", new_name, max_age=86400)
        return resp
        
    return render(request, "store_settings.html", {"current_name": current_name, "current_code": current_code, "current_desc": current_desc})


# =========================
# ADMIN APPROVAL VIEWS
# =========================

def admin_approval(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "login":
            name = request.POST.get("admin_name")
            password = request.POST.get("admin_password")
            # Reverted to strict '1122' as requested
            if name == "SHOP NEXT" and password == "1122":
                request.session['admin_logged_in'] = True
                return redirect("admin_approval")
            else:
                return render(request, "admin_approval.html", {"error": "Invalid Details!"})
        
        elif action == "logout":
            if 'admin_logged_in' in request.session:
                del request.session['admin_logged_in']
            return redirect("admin_approval")

    is_logged_in = request.session.get('admin_logged_in', False)
    pending_products = Product.objects.filter(is_approved=False).order_by('-id')
    live_products = Product.objects.filter(is_approved=True).order_by('-id')
    all_sellers_list = []
    db_seller_codes = set()
    
    # 1. Fetch DB Sellers
    db_sellers = SellerAccount.objects.all().order_by('-id')
    for s in db_sellers:
        all_sellers_list.append({
            "store_name": s.store_name,
            "store_code": s.store_code,
            "legal_name": s.legal_name or "N/A",
            "username": s.user.username if s.user else "N/A",
            "phone": s.phone or "N/A",
            "email": s.email or "N/A",
            "status": "Active (DB)"
        })
        db_seller_codes.add((s.store_name, s.store_code))
        
    # 2. Fetch Text File Sellers
    if os.path.exists(ROOT_DB_FOLDER):
        for d in os.listdir(ROOT_DB_FOLDER):
            folder_path = os.path.join(ROOT_DB_FOLDER, d)
            if os.path.isdir(folder_path) and d != "s":
                txt_file = os.path.join(folder_path, f"seller_{d}.txt")
                if os.path.exists(txt_file):
                    s_name = s_code = s_email = s_phone = "N/A"
                    with open(txt_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("Store Name:"): s_name = line.split("Store Name:")[1].strip()
                            elif line.startswith("Store Code:"): s_code = line.split("Store Code:")[1].strip()
                            elif line.startswith("Email:"): s_email = line.split("Email:")[1].strip()
                            elif line.startswith("Phone:"): s_phone = line.split("Phone:")[1].strip()
                    
                    if (s_name, s_code) not in db_seller_codes and s_name != "N/A":
                        all_sellers_list.append({
                            "store_name": s_name,
                            "store_code": s_code,
                            "legal_name": "N/A",
                            "username": "System Seller",
                            "phone": s_phone,
                            "email": s_email,
                            "status": "Active (Legacy)"
                        })
                        db_seller_codes.add((s_name, s_code))
    all_complaints = Complaint.objects.all().order_by('-id')
    for c in all_complaints:
        seller_account = SellerAccount.objects.filter(Q(user__username=c.reported_user) | Q(store_name=c.reported_user) | Q(store_code=c.reported_user)).first()
        if seller_account:
            c.store_name = seller_account.store_name
            c.store_code = seller_account.store_code
        else:
            c.store_name = c.reported_user
            c.store_code = "N/A"
            
    all_users = User.objects.filter(socialaccount__isnull=False).distinct().order_by('-id')
    return render(request, "admin_approval.html", {
        "is_logged_in": is_logged_in,
        "pending_products": pending_products,
        "live_products": live_products,
        "all_sellers": all_sellers_list,
        "all_complaints": all_complaints,
        "all_users": all_users
    })

@csrf_exempt
def approve_product(request):
    if request.method == "POST" and request.session.get('admin_logged_in', False):
        try:
            pid = request.POST.get("pid")
            product = Product.objects.filter(id=pid).first()
            if product:
                product.is_approved = True
                product.save()
                return JsonResponse({"status": "success"})
            return JsonResponse({"status": "error", "message": "Product not found"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)

@csrf_exempt
def manage_product_action(request):
    if request.method == "POST" and request.session.get('admin_logged_in', False):
        try:
            pid = request.POST.get("pid")
            action = request.POST.get("action")
            product = Product.objects.filter(id=pid).first()
            if product:
                if action == "activate":
                    product.is_available = True
                    product.is_admin_deactivated = False
                    product.save()
                    return JsonResponse({"status": "success", "message": "Product Activated"})
                elif action == "deactivate":
                    product.is_available = False
                    product.is_admin_deactivated = True
                    product.save()
                    return JsonResponse({"status": "success", "message": "Product Deactivated"})
                elif action == "delete":
                    product.delete()
                    return JsonResponse({"status": "success", "message": "Product Deleted"})
            return JsonResponse({"status": "error", "message": "Product not found"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)

import shutil

@csrf_exempt
def manage_seller_action(request):
    if request.method == "POST" and request.session.get('admin_logged_in', False):
        try:
            store_code = request.POST.get("store_code")
            action = request.POST.get("action")  # 'activate', 'deactivate', 'delete'
            
            # Check DB record First
            seller = SellerAccount.objects.filter(store_code=store_code).first()
            if seller:
                if action == "activate":
                    seller.is_approved = True
                    seller.save()
                    return JsonResponse({"status": "success", "message": "Seller Activated"})
                elif action == "deactivate":
                    seller.is_approved = False
                    seller.save()
                    return JsonResponse({"status": "success", "message": "Seller Deactivated"})
                elif action == "delete":
                    seller.delete()
                    return JsonResponse({"status": "success", "message": "Seller Deleted"})
                    
            else:
                # Check Legacy Folders
                if os.path.exists(ROOT_DB_FOLDER):
                    for d in os.listdir(ROOT_DB_FOLDER):
                        folder_path = os.path.join(ROOT_DB_FOLDER, d)
                        if os.path.isdir(folder_path) and d != "s":
                            txt_file = os.path.join(folder_path, f"seller_{d}.txt")
                            if os.path.exists(txt_file):
                                s_code = None
                                with open(txt_file, "r", encoding="utf-8") as f:
                                    for line in f:
                                        if line.startswith("Store Code:"): 
                                            s_code = line.split("Store Code:")[1].strip()
                                            break
                                if s_code == store_code:
                                    if action == "delete":
                                        shutil.rmtree(folder_path)
                                        return JsonResponse({"status": "success", "message": "Legacy Seller Deleted"})
                                    else:
                                        return JsonResponse({"status": "success", "message": f"Legacy Seller {action}d (Note: Legacy records stay active unless deleted)"})
                                        
            return JsonResponse({"status": "error", "message": "Seller not found"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
            
    return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)

def editor(request):
    return render(request, 'editor.html')

from django.views.decorators.clickjacking import xframe_options_exempt # type: ignore

@xframe_options_exempt
def chat_editor(request):
    return render(request, '3.html')



