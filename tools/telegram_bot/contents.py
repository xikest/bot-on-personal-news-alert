from tools.file_manager.functions import FilesF
from typing import Any, Optional,List, Union
from dataclasses  import dataclass
# from tools.telegram_bot.telegram_bot import TelegramBot
from tools.time.time import Timer
import asyncio
import telegram

from tools.translate import Kakao, Papago

from .summary import Wsj

@dataclass
class Context:
        title:Optional[str]=None
        content:List[Any] = None
        label:Optional[str] = None
        summary:List[Any] = None
        descr:Optional[str] = None
        dtype:Optional[str] = None
        enable_translate:bool = False
        enable_summary:bool = False
        botChatId:Optional[str] = None

class Contents(list): 
    """
    import feedparser
    def make_content(rss_url):
      yield [Content(feed.summary, feed.title, feed.link) for feed in feedparser.parse(rss_url).entries]
          
    
    rss_url = 'https://back.nber.org/rss/releases.xml'
    
    contents = Contents()
    contents.addFromList(make_content(rss_url))
    
    contents.saveContentsDict()
    
    contents.loadContentsDict()
    """
    def __init__(self, context:Context=None):
        super().__init__()
        self.append(context)
        
    def addContext(self, context:Context=None):
        self.append(context)

    def saveContents(self, context:Context, fileName:str='contents_list'):
        sent_list=list(self.loadContents())
        sent_list.append(context)
        if len(sent_list)> 10000 : sent_list.pop()  # 버퍼 10000개로 제한
        FilesF.Pickle.save_to_pickle(sent_list, f'{fileName}')
        # return print('saved backup')

    def loadContents(self, fileName:str='contents_list'):
        try:
            # print('loaded files')
            yield from FilesF.Pickle.load_from_pickle(f'{fileName}')
        except:
            # print('loaded fail')
            yield from []
        

    
    async   def sendTo(self, token:str, delay:Union[int, float]=0) -> None:
                context:Context = self.pop()
                bot = telegram.Bot(token)
                # print('send start')
                if context not in self.loadContents():
                    self.saveContents(context=context)
                    # print('no in loading')
                    #await asyncio.sleep(Timer.sleepToRelease(context.release_time, delay))         
                    try:           
                        context = self.summary(context)  # 요약본 생성
                        while len(context.content) > 0:   
                            # print('loop start')   
                            # print(context)            
                            if context.dtype == 'img': 
                                await asyncio.sleep(5)
                                await bot.send_photo(chat_id=context.botChatId, photo=context.content.pop(0))
                                
                            elif context.dtype == 'msg':
                                if context.enable_translate == True:
                                    msg = f"#{context.label}\n{await self.translate(context.summary.pop(0))}\n\n{context.content.pop(0)}"
                                    # print(f'translate : {msg}')
                                elif context.enable_translate == False :msg = f"#{context.label}\n\n{context.content.pop(0)}"
                                # print(f'msg : {msg}')
                                await asyncio.sleep(5)
                                await bot.send_message(chat_id=context.botChatId, text=msg) #'msg'
                            else: raise Exception("dtype이 정의되지 않았습니다.")
                    except:pass
                return None
            
    async def translate(self, txt:str) -> str:
        try:res = await Papago('en').translate(txt)
            # print(res)
        except: res = await Kakao('en').translate(txt)
        return res
    
    def summary(self, context:Context):
        if context.enable_summary==True:
            if context.label == 'WSJ':   #WSJ 기사 요약
                context.summary = [Wsj(content).summary() for content in context.content]
                    # context.summary.append(Wsj(content).summary())
                context.enable_translate=True # 번역할 것인지 
                # print(f'summariziong: {context}')
        return context 