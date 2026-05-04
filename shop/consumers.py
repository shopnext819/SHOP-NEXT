import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User  # type: ignore
from .models import Message, UserStatus, BlockedUser

@database_sync_to_async
def get_user(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None

@database_sync_to_async
def set_online(user, is_online):
    UserStatus.objects.update_or_create(user=user, defaults={"is_online": is_online})

@database_sync_to_async
def is_user_blocked(receiver, user):
    return BlockedUser.objects.filter(user=receiver, blocked=user).exists()

@database_sync_to_async
def delete_message_db(msg_id):
    Message.objects.filter(id=msg_id).delete()

@database_sync_to_async
def mark_seen_db(msg_id):
    msg = Message.objects.filter(id=msg_id).first()
    if msg:
        msg.seen = True
        msg.save()
        return msg.id
    return None

@database_sync_to_async
def create_msg(sender, receiver, text, image, product_id):
    return Message.objects.create(
        sender=sender,
        receiver=receiver,
        text=text,
        image=image,
        product_id=product_id
    )

@database_sync_to_async
def get_chat_history(user1_username, user2_username, product_id):
    from django.db.models import Q  # type: ignore
    from django.contrib.auth.models import User  # type: ignore
    try:
        user1 = User.objects.get(username=user1_username)
        user2 = User.objects.get(username=user2_username)
        messages = Message.objects.filter(
            (Q(sender=user1, receiver=user2) | Q(sender=user2, receiver=user1)),
            product_id=product_id
        ).order_by('timestamp')
        
        return [
            {
                "id": m.id,
                "sender": m.sender.username,
                "message": m.text,
                "image": m.image,
                "seen": m.seen
            }
            for m in messages
        ]
    except Exception:
        return []

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Handle anonymous users securely
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
            
        self.user = self.scope["user"]
        self.other = self.scope['url_route']['kwargs']['username']
        self.product_id = self.scope['url_route']['kwargs']['product_id']

        users = sorted([self.user.username, self.other])
        self.room_name = f"{users[0]}_{users[1]}_{self.product_id}"
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await set_online(self.user, True)

        await self.accept()
        
        history = await get_chat_history(self.user.username, self.other, self.product_id)
        await self.send(text_data=json.dumps({
            "type": "chat_history",
            "messages": history
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        await set_online(self.user, False)

    async def receive(self, text_data):
        data = json.loads(text_data)
        receiver = await get_user(self.other)

        if not receiver:
            return # User doesn't exist

        # 🚫 BLOCK CHECK
        is_blocked = await is_user_blocked(receiver, self.user)

        if is_blocked:
            return

        # 🎤 VOICE MESSAGE
        if data.get("voice"):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "voice_msg",
                    "audio": data["voice"],
                    "sender": self.user.username
                }
            )
            return

        # 🗑 DELETE MESSAGE
        if data.get("delete"):
            await delete_message_db(data["id"])

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "delete_msg",
                    "id": data["id"],
                    "delete": True
                }
            )
            return

        # 🟡 TYPING
        if data.get("typing"):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing",
                    "user": self.user.username
                }
            )
            return

        # ✔ SEEN
        if data.get("seen"):
            msg_id = await mark_seen_db(data["id"])
            if msg_id:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "seen_update",
                        "id": msg_id
                    }
                )
            return

        # 📞 CALL SIGNALING
        if data.get("type") == "call-signal":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "call_signal",
                    "signal": data.get("signal")
                }
            )
            return

        # NORMAL MESSAGE
        msg = await create_msg(
            self.user,
            receiver,
            data.get("message"),
            data.get("image"),
            self.product_id
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": data.get("message"),
                "image": data.get("image"),
                "sender": self.user.username,
                "id": msg.id
            }
        )

        # 🤖 AI AUTO REPLY (BASIC)
        if data.get("message") and "price" in data.get("message").lower():
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": "Price is fixed 💰",
                    "sender": "AI"
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def typing(self, event):
        await self.send(text_data=json.dumps(event))

    async def seen_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def call_signal(self, event):
        await self.send(text_data=json.dumps({
            "type": "call-signal",
            "signal": event["signal"]
        }))

    async def voice_msg(self, event):
        await self.send(text_data=json.dumps(event))

    async def delete_msg(self, event):
        await self.send(text_data=json.dumps(event))
