import os
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from app.services.agent_engine import NIDAAgentEngine

router = APIRouter()

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "dummy_token")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "dummy_secret")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@router.post("/api/line/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_str = body.decode("utf-8")
    
    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        # In development without real keys, just log and return 200 so LINE stops retrying
        print("Invalid signature. Check your channel secret.")
        
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    session_id = f"line_{event.source.user_id}"
    
    # Process with NIDAAgentEngine synchronously for simplicity in webhook
    # In production, use async or push to queue if taking > 3 seconds
    try:
        # We will collect the stream and send it back once
        full_reply = ""
        for chunk in NIDAAgentEngine.execute_chat_stream(
            session_id=session_id,
            user_message=user_message
        ):
            full_reply += chunk
            
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=full_reply)
        )
    except Exception as e:
        print(f"Error handling LINE message: {e}")
