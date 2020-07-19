import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async

from .models import Thread, ChatMessage


class ChatConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        print("connnected", event)

        me = self.scope['user']
        other = self.scope['url_route']['kwargs']['username']
        thread_obj = await self.get_thread_obj(me, other)
        self.thread_obj = thread_obj
        chat_room = f"thread_{thread_obj.id}"  # name for chat room
        self.chat_room = chat_room
        await self.send({
            "type": "websocket.accept",
        })
        await self.channel_layer.group_add(
            chat_room,
            self.channel_name
        )

    async def websocket_receive(self, event):
        front_text = event.get("text", None)
        if front_text is not None:
            loaded_data_dict = json.loads(front_text)
            loaded_data_msg = loaded_data_dict['message']
            user = self.scope['user']
            username = "default"
            if user.is_authenticated:
                username = user.username
            my_response = {
                "message": loaded_data_msg,
                "username": username
            }
            self.create_chat_message(loaded_data_msg)
            print("sending data", my_response)
            await self.channel_layer.group_send({
                self.chat_room,
                {
                   "type": "chat_message",
                   "text": json.dumps(my_response)
                }
            })


    async def websocket_disconnect(self, event):
        print("disconnected", event)
        # await self.channel_layer.group_discard(
        #     #channel name
        # )

    async def chat_message(self, event):
        await self.send({
            "type": "websocket.send",
            "text": event["text"]
        })
        

    @database_sync_to_async
    def get_thread_obj(self, user, other_username):
        return Thread.objects.get_or_new(user, other_username)[0]

    @database_sync_to_async
    def create_chat_message(self,  msg):
        thread_obj = self.thread_obj
        me = self.scope['user']
        return ChatMessage.objects.create(
            thread=thread_obj,
            user=me,
            message=msg
        )
