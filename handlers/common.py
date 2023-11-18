from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import openai
import requests
from bs4 import BeautifulSoup
from handlers import tools

router = Router()


class CurrentFunction(StatesGroup):
    editing_post = State()
    parsing_channels = State()
    adding_channels = State()
    limiting_posts = State()


@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        text="Привет! Мои возможности: \n"
             "1) Чтобы получить пост-рекомендацию на статью, просто пришли мне на нее ссылку:) \n"
            "2) Чтобы добавить каналы, у которых нужно спарсить посты, напиши /add_channels"
    )


@router.message(Command("add_channels"))
async def answer_add_channels(message, state):
    await message.answer("Отправь теги каналов, посты с которых нужно спарсить, одним сообщением через пробел")
    await state.set_state(CurrentFunction.adding_channels)


@router.message(CurrentFunction.adding_channels)
async def adding_channels(message, state):
    await state.update_data(channels=message.text.split())
    await message.answer("Отправь число - ограничение по постам, котоыре надо парсить с этих каналов")
    await state.set_state(CurrentFunction.limiting_posts)


@router.message(CurrentFunction.limiting_posts)
async def parsing_channels(message, state):
    limit = int(message.text)
    user_data = await state.get_data()
    channels = user_data['channels']
    await state.set_state(state=None)
    await message.answer("Начал парсить...",
                         parse_mode="Markdown")
    post_list = await tools.get_posts(channels, limit=limit)
    print(len(post_list))
    for post in post_list[: min(len(post_list), 10)]:
        await message.answer(
                             "Ссылка на пост: " + f"https://t.me/{post['channel_name']}/{post['id']}" + "\n" +
                             "Реакций: " + str(post['reactions'])
                             )
    try:
        pass
    except:
        await message.answer(
                         "Ошибка во время парсинга :(",
                         parse_mode="Markdown")


@router.message(StateFilter(None))
async def making_post(message: Message):
    global messages
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
        await message.answer('Парсим статью...')
        article_elements = soup.find_all('article')
        header_elements = soup.find_all('h1')  # Считаем еще и заголовки
        # Соберем элементы в одну статью
        article_text = ''
        header_text = ''
        for element in article_elements:
            article_text += '\n' + element.get_text()

        for element in header_elements:
            header_text += '\n' + element.get_text()
        await message.answer('Статья получена! Делаем по ней summary...')
        article_summary = tools.summarization(article_text)
        await message.answer('Саммари сделано!')

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
        await message.answer('Правки приняты к обработке')
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
                {"role": "assistant", "content": soobsh  # Укорачиваем, чтобы ChatGPT не ругался
                 }
            )
            # Отправляем ему все вместе
            await message.answer('Делаем пост...')
            completion = openai.ChatCompletion.create(model=model,
                                                      messages=messages,
                                                      )
        else:
            completion = openai.ChatCompletion.create(model=model,
                                                      messages=messages,
                                                      )
        # completion.choices представляет собой список возможных вариантов ответов, сгенерированных моделью чат-бота. Каждый вариант ответа содержит свойство message, которое представляет собой объект сообщения с двумя свойствами: role (роль отправителя) и content (содержание сообщения).
        # Мы берем первый (нулевой) элемент-первый вариант ответа, сгенерированный моделью.
        await message.answer("Пост сделан!")
        decoded_response = completion.choices[0].message.content.encode('utf-8').decode('utf-8')
        messages.append({"role": "assistant",
                         "content": decoded_response})
        await message.answer(decoded_response)
    # Если слишком часто отправляем запросы, он начинает ругаться
    except openai.error.RateLimitError:
        await message.answer('Лимит по времени, напиши еще раз')
    except openai.error.ServiceUnavailableError:
        await message.answer('Сервера OpenAI недоступны, повтори позже')
