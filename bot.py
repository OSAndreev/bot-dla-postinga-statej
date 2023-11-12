import telebot
import openai
import requests
from bs4 import BeautifulSoup


openai.api_key = "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"

def summarization(article_text):
    model = "gpt-3.5-turbo-1106"
    sum_messages = []
    prompt = 'Я отправлю тебе статью на русском языке. Тебе нужно будет сделать ее краткую версию,минимальная длина которой 100 токенов, а максимальная длина не больше 300 токенов. Вот статья:'
    sum_messages.append(
        {"role": "assistant",
         "content": prompt + article_text})
    '''WHITESPACE_HANDLER = lambda k: re.sub('\s+', ' ', re.sub('\n+', ' ', k.strip()))

    model_name = "csebuetnlp/mT5_multilingual_XLSum"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    input_ids = tokenizer(
        [WHITESPACE_HANDLER(article_text)],
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=512
    )["input_ids"]

    output_ids = model.generate(
        input_ids=input_ids,
        max_length=84,
        no_repeat_ngram_size=2,
        num_beams=4
    )[0]

    summary = tokenizer.decode(
        output_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )'''
    completion = openai.ChatCompletion.create(model=model,
                                              messages=sum_messages,
                                              )

    summary = completion.choices[0].message.content.encode('utf-8').decode('utf-8')
    return summary

bot = telebot.TeleBot('6553287137:AAG7shwwN9Vlun9US55pHdJ8dXscF3lLAV8')
@bot.message_handler(content_types=['text'])
# В этом участке кода мы объявили приемщика для текстовых сообщений и метод их обработки.
# Поле content_types может принимать разные значения, и не только одно, например
# @bot.message_handler(content_types=['text', 'document', 'audio'])
def get_text_messages(message):
    global messages
    if message.text == "/start":
        bot.send_message(message.from_user.id,
                         "Привет! Могу помочь тебе с написанием поста-рекомендации на статью. Просто пришли мне на нее ссылку:)",
                         parse_mode="Markdown")
    else:

        model = "gpt-3.5-turbo"  # Подключаем ChatGPT
        # Получаем HTML-код статьи
        url = message.text
        # Если в запросе есть ссылка - парсим, иначе просто отправляем запрос
        if '/' in url:
            messages = []
            response = requests.get(url)
            html = response.text

            # Создаем объект BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Находим элементы, содержащие текст статьи
            bot.send_message(message.from_user.id, 'Парсим статью...', parse_mode="Markdown")
            article_elements = soup.find_all('article')
                               #+ soup.find_all("div", { "id": "post-content-body"})  # Здесь 'p' можно менять на тег, который нужен нам. Можно брать заголовки, но как будто нам они не нужны.
            # div - блочный элемент
            header_elements = soup.find_all('h1')  # Считаем еще и заголовки
            # Соберем элементы в одну статью
            article_text = ''
            header_text = ''
            for element in article_elements:
                article_text += '\n' + element.get_text()

            for element in header_elements:
                header_text += '\n' + element.get_text()
            bot.send_message(message.from_user.id, 'Статья получена! Делаем по ней саммари...', parse_mode="Markdown")
            article_summary = summarization(article_text)
            bot.send_message(message.from_user.id, 'Саммари сделано!', parse_mode="Markdown")


            # Prompt - это текстовый запрос, который мы отправляем нейросети, чтобы получить от нее нужный ответ или выполнение задачи.

            prompt = "Представь, что ты копирайтер телеграм канала. У тебя есть несколько примеров постов в свой телеграм канал по статьям." \
                     "Сначала ты посмотришь их, а затем тебе надо будет написать такой же короткий пост про статью," \
                     "короткое содержание которой я отправлю тебе. Вот примеры коротких постов: "
            with open('post_examples.txt', 'r', encoding='utf-8') as file:
                posts = file.read()

            messages.append(
                {"role": "assistant",
                 "content": prompt + posts})  # assistant - значит он сохраняет контекст."role" (роль отправителя - "system", "user" или "assistant") и "content" (содержание сообщения).

        else:
            messages.append({"role": "assistant", "content": message.text})
            bot.send_message(message.from_user.id, 'Правки приняты к обработке', parse_mode="Markdown")
        try:
            # Если в запросе была ссылка, то производим операции с ней
            if '/' in message.text:
                # Добавляем к сообщениям статью

                soobsh = "Теперь по примеру постов, которые я отправил тебе, напиши короткий пост (максимум 200 токенов) по этой статье (которую писал не я), " \
                          "чтобы заинтересовать подписчиков телеграм канала в прочтении статьи." \
                          " В начале напиши заголовок, и окружи его символами '*'. Важные слова, которые стоило бы выделить, окружи символами '*'.Используй смайлики в умеренном количестве. В конце обязательно напиши \"Ссылка на статью:{0}\": \n".format(url) \
                          + "Заголовок: " + header_text + "\n" \
                          + "Текст статьи: " + "\n" + article_summary
                if len(soobsh) >= 2500:
                    soobsh = soobsh[:2500]
                messages.append(
                    {"role": "assistant", "content": soobsh[:2500]  # Укорачиваем, чтобы ChatGPT не ругался
                     }
                )
                # Отправляем ему все вместе
                bot.send_message(message.from_user.id, 'Делаем пост...', parse_mode="Markdown")
                completion = openai.ChatCompletion.create(model=model,
                                                          messages=messages,
                                                          )
            else:
                print('Вносим правки...')
                print(messages)
                completion = openai.ChatCompletion.create(model=model,
                                                          messages=messages,
                                                          )
            # completion.choices представляет собой список возможных вариантов ответов, сгенерированных моделью чат-бота. Каждый вариант ответа содержит свойство message, которое представляет собой объект сообщения с двумя свойствами: role (роль отправителя) и content (содержание сообщения).
            # Мы берем первый (нулевой) элемент-первый вариант ответа, сгенерированный моделью.
            bot.send_message(message.from_user.id, "Пост сделан!", parse_mode="Markdown")
            decoded_response = completion.choices[0].message.content.encode('utf-8').decode('utf-8')
            bot.send_message(message.from_user.id, decoded_response, parse_mode="Markdown")
        # Если слишком часто отправляем запросы, он начинает ругаться
        except openai.error.RateLimitError:
            bot.send_message(message.from_user.id, 'Лимит по времени, напиши еще раз')



bot.polling(none_stop=True)

#bot.polling() запускает цикл опроса, который проверяет наличие новых входящих сообщений или событий от пользователей.
# Бот будет постоянно опрашивать серверы Telegram для обновлений.