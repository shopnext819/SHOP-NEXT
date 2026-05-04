from django.contrib import admin
from .models import Product, Cart, UserProfile, SellerAccount, Message

admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(UserProfile)
admin.site.register(SellerAccount)
admin.site.register(Message)
