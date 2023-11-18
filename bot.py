import telebot
import openai
import requests
from bs4 import BeautifulSoup
import post_parser

openai.api_key = "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"

def summarization(article_text):
    model = "gpt-3.5-turbo-1106"
    sum_messages = []
    prompt = 'Я отправлю тебе статью на русском языке. Тебе нужно будет сделать ее краткую версию,минимальная длина которой 100 токенов, а максимальная длина не больше 300 токенов. Вот статья:'
    sum_messages.append(
        {"role": "assistant",
         "content": prompt + article_text})
    try:
        completion = openai.ChatCompletion.create(model=model,
                                                  messages=sum_messages,
                                                  )
    except openai.error.InvalidRequestError:
        completion = openai.ChatCompletion.create(model=model,
                                                  messages=sum_messages[:7000],
                                                  )

    summary = completion.choices[0].message.content.encode('utf-8').decode('utf-8')
    return summary


bot = telebot.TeleBot('6937186847:AAHGhMg2pPSvcAOsISPu8nun_8pyXWBNNV8')


@bot.message_handler(content_types=['text'])
# В этом участке кода мы объявили приемщика для текстовых сообщений и метод их обработки.
# Поле content_types может принимать разные значения, и не только одно, например
# @bot.message_handler(content_types=['text', 'document', 'audio'])
def get_text_messages(message):
    global messages, channels, limit
    if message.text == "/start":
        bot.send_message(message.from_user.id,
                         "Привет! Могу помочь тебе с написанием поста-рекомендации на статью. Просто пришли мне на нее ссылку:)",
                         parse_mode="Markdown")
    elif message.text == "/add_channels":
        bot.send_message(message.from_user.id,
                         "Напиши через пробел никнеймы каналов, которые ты хочешь мониторить",
                         parse_mode="Markdown")

        bot.register_next_step_handler(message, handle_limit)
        bot.register_next_step_handler(message, handle_channels)


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
            # + soup.find_all("div", { "id": "post-content-body"})  # Здесь 'p' можно менять на тег, который нужен нам. Можно брать заголовки, но как будто нам они не нужны.
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
                         " В начале напиши заголовок, и окружи его символами '*'. Важные слова, которые стоило бы выделить, окружи символами '*'.Используй смайлики в умеренном количестве. В конце обязательно напиши \"Ссылка на статью:{0}\": \n".format(
                    url) \
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
            messages.append({"role": "assistant",
                             "content": decoded_response})
            bot.send_message(message.from_user.id, decoded_response, parse_mode="Markdown")
        # Если слишком часто отправляем запросы, он начинает ругаться
        except openai.error.RateLimitError:
            bot.send_message(message.from_user.id, 'Лимит по времени, напиши еще раз')
        except openai.error.ServiceUnavailableError:
            bot.send_message(message.from_user.id, 'Сервера OpenAI недоступны, повтори позже')


def handle_limit(message):
    global limit
    bot.send_message(message.from_user.id,
                     "Начал парсить...",
                     parse_mode="Markdown")
    try:
        post_list = post_parser.get_posts(channels, limit=limit)
        for post in post_list[: len(post_list) % 10]:
            bot.send_message(message.from_user.id,
                             "Текст: " + post['text'][100] + "...\n" + \
                             "Канал: @" + post['channel_name'],
                             parse_mode="Markdown")
    except:
        bot.send_message(message.from_user.id,
                         "Ошибка во время парсинга :(",
                         parse_mode="Markdown")

def handle_channels(message):
    global channels
    channels = message.text.split()

    bot.send_message(message.from_user.id,
                     "Напиши, сколько последних постов у каждого канала тебе нужно спарсить",
                     parse_mode="Markdown")

bot.polling(none_stop=True)

# bot.polling() запускает цикл опроса, который проверяет наличие новых входящих сообщений или событий от пользователей.
# Бот будет постоянно опрашивать серверы Telegram для обновлений.
