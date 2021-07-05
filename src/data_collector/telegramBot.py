# library: python-telegram-bot
import telegram
my_token = ''  # bot token
chat_id = '' # telegram group or chat id
def sendTelegramMsg(msg, chat_id=chat_id, token=my_token):
	bot = telegram.Bot(token=token)
	bot.sendMessage(chat_id=chat_id, text=msg)
