from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import os


# =========================
# PRODUCT MODEL
# =========================
class Product(models.Model):
    seller = models.ForeignKey('SellerAccount', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    price = models.IntegerField()
    stock = models.IntegerField(default=0)
    free_items = models.CharField(max_length=100, blank=True, null=True)
    warranty_policy = models.TextField(blank=True, null=True)
    return_policy = models.TextField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=True)
    is_admin_deactivated = models.BooleanField(default=False)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    image2 = models.ImageField(upload_to='products/', null=True, blank=True)
    image3 = models.ImageField(upload_to='products/', null=True, blank=True)
    image4 = models.ImageField(upload_to='products/', null=True, blank=True)
    image5 = models.ImageField(upload_to='products/', null=True, blank=True)
    image6 = models.ImageField(upload_to='products/', null=True, blank=True)
    video = models.FileField(upload_to='products/videos/', null=True, blank=True)

    def __str__(self):
        return self.name


# =========================
# CART MODEL
# =========================
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)


# =========================
# USER PROFILE MODEL
# =========================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    birthday = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    source = models.CharField(max_length=200, blank=True)
    custom_source = models.CharField(max_length=200, blank=True)
    question = models.TextField(blank=True)

    is_completed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # ===== AUTO TXT FILE SAVE =====
        if self.first_name:
            folder_path = os.path.dirname(__file__)
            file_name = f"{self.first_name.lower()}.txt"
            file_path = os.path.join(folder_path, file_name)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("USER PROFILE INFORMATION\n")
                f.write("-------------------------\n")
                f.write(f"Username: {self.user.username}\n")
                f.write(f"First Name: {self.first_name}\n")
                f.write(f"Last Name: {self.last_name}\n")
                f.write(f"Birthday: {self.birthday}\n")
                f.write(f"Phone: {self.phone}\n")
                f.write(f"Source: {self.source}\n")
                f.write(f"Custom Source: {self.custom_source}\n")
                f.write(f"Question: {self.question}\n")

    def __str__(self):
        return self.user.username


# =========================
# SELLER ACCOUNT MODEL
# =========================
class SellerAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Store Info
    store_name = models.CharField(max_length=200)
    store_code = models.CharField(max_length=50, unique=True)
    store_desc = models.TextField()
    category = models.CharField(max_length=100)
    
    # Contact & Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=20)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Identity KYC
    legal_name = models.CharField(max_length=200)
    id_no = models.CharField(max_length=100, blank=True, null=True)
    tax_no = models.CharField(max_length=100, blank=True, null=True)
    dob = models.DateField(null=True, blank=True)
    seller_type = models.CharField(max_length=50, default='personal')
    business_address = models.TextField(blank=True, null=True)
    
    # Payout Details
    payment_type = models.CharField(max_length=50) # 'bank' or 'online'
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_no = models.CharField(max_length=100, blank=True, null=True)
    iban = models.CharField(max_length=100, blank=True, null=True)
    bank_code = models.CharField(max_length=100, blank=True, null=True)
    bank_branch = models.CharField(max_length=100, blank=True, null=True)
    wallet_name = models.CharField(max_length=100, blank=True, null=True)
    wallet_no = models.CharField(max_length=100, blank=True, null=True)
    
    # Social Links
    facebook_link = models.URLField(blank=True, null=True)
    instagram_link = models.URLField(blank=True, null=True)
    
    # Media/Images (Stored as paths/URLs for now, or ImageField later if MEDIA_URL is configured)
    banner_image = models.ImageField(upload_to='seller_banners/', blank=True, null=True)
    profile_image = models.ImageField(upload_to='seller_profiles/', blank=True, null=True)
    id_front = models.ImageField(upload_to='seller_kyc/', blank=True, null=True)
    id_back = models.ImageField(upload_to='seller_kyc/', blank=True, null=True)
    checkbook_image = models.ImageField(upload_to='seller_kyc/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.store_name} ({self.user.username})"


# =========================
# INBOX / MESSAGE MODEL
# =========================
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_msg")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_msg")

    product_id = models.IntegerField(null=True, blank=True)

    text = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)

    seen = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} -> {self.receiver} ({self.product_id})"


class UserStatus(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_online = models.BooleanField(default=False)

class BlockedUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocker")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocked")

class VoiceMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="voice_sender")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="voice_receiver")
    audio = models.TextField()  # base64
    timestamp = models.DateTimeField(auto_now_add=True)

# =========================
# WEBRTC SIGNALING MODEL
# =========================
class CallSignal(models.Model):
    caller = models.CharField(max_length=200) # Sender Identity
    callee = models.CharField(max_length=200) # Target Identity
    signal_type = models.CharField(max_length=50) # 'offer', 'answer', 'candidate', 'call_ring', 'reject', 'end'
    payload = models.TextField() # JSON payload 
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.signal_type} from {self.caller} to {self.callee}"

# =========================
# COMPLAINT MODEL
# =========================
class Complaint(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaint_sender")
    reported_user = models.CharField(max_length=100, blank=True, null=True)
    subject = models.CharField(max_length=200, default="User Report")
    body = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

def __str__(self):
        return f"Complaint by {self.sender.username} - {self.subject}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()