import re

with open(r'c:\SHOP NEXT\shop\views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Q import
if 'from django.db.models import Q' not in content:
    content = content.replace('from django.shortcuts import render, redirect', 'from django.db.models import Q\nfrom django.shortcuts import render, redirect')

# Replace old inbox and chat views
# They are between "def inbox(request):" and "# ==========================================\n# WEBRTC NATIVE SIGNALING VIEWS"
pattern = r"def inbox\(request\):.*?# ==========================================\n# WEBRTC NATIVE SIGNALING VIEWS"

new_views = '''def chat(request, username, product_id):
    return render(request, "chat.html", {
        "other": username,
        "product_id": product_id,
        "me": request.user.username
    })

def inbox(request):
    msgs = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by("-timestamp")

    users = {}

    for m in msgs:
        other = m.receiver if m.sender == request.user else m.sender

        key = f"{other.username}_{m.product_id}"

        if key not in users:
            users[key] = {
                "user": other.username,
                "product": m.product_id,
                "last": m.text or "📷 Image"
            }

    return render(request, "inbox.html", {"chats": users.values()})

# ==========================================
# WEBRTC NATIVE SIGNALING VIEWS'''

content = re.sub(pattern, new_views, content, flags=re.DOTALL)

# Remove the previously appended chat_room/chat alias at the bottom
content = re.sub(r'def chat\(request, room\):.*?\}\)', '', content, flags=re.DOTALL)

with open(r'c:\SHOP NEXT\shop\views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("views.py updated")
