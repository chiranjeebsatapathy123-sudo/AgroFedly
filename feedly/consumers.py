import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return
            
        # Join user-specific group
        self.user_group_name = f"user_{self.scope['user'].id}"
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # Join organization groups if available
        self.org_groups = []
        if hasattr(self.scope['user'], 'organization_memberships'):
            # In a real async environment, we need database_sync_to_async to query
            pass # We'll do it safely

        # For simplicity and safety in async WebSocket consumers without DB queries,
        # we can just listen to the user group, and signals.py will loop through org members.
        
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    # Receive message from room group
    async def notification(self, event):
        message = event["message"]
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "message": message
        }))

class BaseOrgConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return
            
        # Simplest approach for secure broadcast without DB query in async context:
        # We broadcast to the user's ID group. The backend signal publisher queries
        # all users in the organization and sends messages to their individual user groups.
        self.user_group_name = f"{self.topic_prefix}_{self.scope['user'].id}"
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def broadcast(self, event):
        await self.send(text_data=json.dumps(event["data"]))


class LogisticsConsumer(BaseOrgConsumer):
    topic_prefix = "logistics_user"


class AgricultureConsumer(BaseOrgConsumer):
    topic_prefix = "agri_user"
