from django.urls import path  # type: ignore
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("product/<int:product_id>/", views.product_detail, name="product_detail"),

    # Cart
    path("add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart, name="cart"),
    path("remove/<int:index>/", views.remove_from_cart, name="remove_from_cart"),

    # Inbox
    path("inbox/", views.inbox, name="inbox"),

    # Chat
    path("chat/<str:username>/<int:product_id>/", views.chat, name="chat"),
    path("block/<str:username>/", views.block_user, name="block_user"),
    path("report/<str:username>/", views.report_user, name="report_user"),
    path("chats-list/", views.chats_list, name="chats_list"),

    # WebRTC Signaling
    path("rtc/signal/", views.send_signal, name="send_signal"),
    path("rtc/poll/", views.poll_signals, name="poll_signals"),

    # Seller Center
    path("seller-center/", views.seller_center, name="seller_center"),
    path("seller-register/", views.seller_register, name="seller_register"),
    path("seller-login/", views.seller_login, name="seller_login"),
    path("seller-dashboard-home/", views.seller_dashboard_home, name="seller_dashboard_home"),
    path("update-seller-settings/", views.update_seller_settings, name="update_seller_settings"),
    path("update-product/", views.update_product, name="update_product"),
    path("delete-product/", views.delete_product, name="delete_product"),
    path("store-settings/", views.store_settings, name="store_settings"),
    
    # Simple Pages
    path("help/", views.help_page, name="help"),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path("profile/", views.profile, name="profile"),
    path("complete-onboarding/", views.complete_onboarding, name="complete_onboarding"),


    # Admin Approval
    path("admin-approval/", views.admin_approval, name="admin_approval"),
    path("approve-product/", views.approve_product, name="approve_product"),
    path("manage-product-action/", views.manage_product_action, name="manage_product_action"),
    path("manage-seller-action/", views.manage_seller_action, name="manage_seller_action"),
    
    # Editor
    path('editor/', views.editor, name="editor"),
    path('chat-editor/', views.chat_editor, name="chat_editor"),
]