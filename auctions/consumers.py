import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

class AuctionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.auction_id = self.scope['url_route']['kwargs']['auction_id']
        self.room_group_name = f'auction_{self.auction_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        pass  # Not needed - bids are placed via HTTP POST

    # Receive message from room group
    async def bid_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'bid_update',
            'bid_amount': event['bid_amount'],
            'bidder': event['bidder'],
            'bid_time': event['bid_time'],
            'current_price': event['current_price']
        }))
