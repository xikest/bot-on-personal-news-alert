import telegram
import logging
import hashlib
import re
from datetime import datetime
from .assistant import Assistant
from bot.definition_obj import Context
from tools.gcp.firestoremanager import FirestoreManager

def get_today_date():
    today = datetime.today()
    return today.strftime('%Y-%m-%d')


class Handler:
    def __init__(self, context: Context, token: str, gpt_key: str, gpt_model:str, firestore_auth:str, ydown_url:str, storage_name:str):
        self.context = context  
        self._token = token
        self._gpt_key = gpt_key    
        self._gpt_model = gpt_model
        self._ydown_url = ydown_url
        self._storage_name = storage_name
        self.firestore = FirestoreManager(firestore_auth)
            
    async def send_content(self, collection_name) -> None:
        def url_to_doc_key_sha256(url: str) -> str:
            return hashlib.sha256(url.encode('utf-8')).hexdigest()
        
        doc_key = url_to_doc_key_sha256(self.context.link)
        try:
            if not self.firestore.is_doc_key_exist(doc_key=doc_key, collection_name = collection_name):
                self.firestore.save_db(doc_key=doc_key, 
                        data_dict={"title": self.context.title, "date":get_today_date(), "link":self.context.link}, 
                        collection_name= collection_name)
                await self._send_msg(self.context)
        except Exception as e:
            logging.error(f"[send_content] Transmission error: {e}")

            
    async def _send_msg(self, context: Context):
        bot = telegram.Bot(self._token)
        try:
            context = await self._processing_with_assistant(context)
            def escape_markdown(text: str) -> str:
                special_chars = r'([_*\[\]()~`>#+\-=|{}.!\\])'
                return re.sub(special_chars, r'\\\1', text)
                
            label = context.label
            label = label.replace(" ","")
            title = context.title
            url =context.link

            if context.trx_mp3:
                label = escape_markdown(label)
                title = escape_markdown(title)
                url = escape_markdown(url)
                message = f"\\#{label}\n[{title}]({url})"
                parse_mode="MarkdownV2"
            else:
                message = f"#{label}\n{title}\n{url}"
                parse_mode=None
                
            await bot.send_message(chat_id=context.bot_chat_id, text=message, parse_mode=parse_mode)

        except Exception as e:
            logging.error(f"[send_msg] Message sending error: {e}")
                
    async def _processing_with_assistant(self, context: Context) -> Context:
        
        assistant = Assistant(api_key=self._gpt_key, gpt_model = self._gpt_model, ydown_apiurl=self._ydown_url,
                              storage_name=self._storage_name)
        if context.trx_mp3:
            try:
                result = await assistant.get_mp3_url(context.link)
                if result:
                    context.title, context.link = result
                    context.title = context.title.rsplit('.', 1)[0]  # 파일 확장자 제거
                else:
                    logging.error("[trx_mp3] Failed to get MP3 URL: Response was None")
            except Exception as e:
                logging.error(f"[trx_mp3] trx_mp3 error: {e}")

                
        if context.enable_translate:
            try:
                if context.title:
                    context.title = assistant.translate_tokr(context.title)
                else:
                    logging.error("[make_summary] Skipping translation: context.title is None")
            except Exception as e:
                logging.error(f"[make_summary] Summary generation error: {e}")

       
        return context
    