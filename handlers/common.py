from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import openai
import requests
from bs4 import BeautifulSoup
from handlers import tools
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from keyboards.simple_row import make_row_keyboard, post_from_post_button
import httpx

router = Router()
scheduler = AsyncIOScheduler()
client = openai.OpenAI(
    api_key='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',
    http_client=httpx.Client(
        proxies="socks5://andreevos22:MJkXWdZjik@166.1.10.179:50101"
    ),
)


class CurrentFunction(StatesGroup):
    editing_post = State()
    making_post = State()
    parsing_channels = State()
    adding_channels = State()
    limiting_posts = State()
    first_parsing_channels = State()
    showing_posts = State()
    filtering_posts_by_type = State()
    filtering_posts_by_words = State()
    getting_post_from_post = State()


@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        text="Привет! Мои возможности: \n"
             "1) Чтобы получить пост-рекомендацию на статью, напиши \"✍️Сделать пост\" \n"
             "2) Чтобы добавить каналы, у которых нужно спарсить посты, напиши \"📢Добавить каналы\"",
        reply_markup=make_row_keyboard(["✍️Сделать пост", "📢Добавить каналы"])
    )


@router.message(F.text.lower() == "📢добавить каналы")
async def answer_add_channels(message, state):
    await message.answer("Отправь теги каналов, посты с которых нужно спарсить, одним сообщением через пробел")
    await state.set_state(CurrentFunction.adding_channels)


@router.message(CurrentFunction.adding_channels)
async def adding_channels(message, state):
    await state.update_data(channels=await tools.extract_channels(message.text))
    await message.answer("Отправь число - глубину первоначального парсинга постов",
                         reply_markup=make_row_keyboard(["10", "30", "50", "100", "200"]))
    await state.set_state(CurrentFunction.limiting_posts)


@router.message(CurrentFunction.limiting_posts)
async def limiting_channels(message, state):
    await state.update_data(limit=int(message.text), updating_channels=False)
    await parsing_channels(message, state)
    await set_order_by(message, state)


@router.message(F.text.lower() == "🏆топ постов")
async def set_order_by(message, state):
    await message.answer("По какой метрике тебе нужно сделать топ?",
                         reply_markup=make_row_keyboard(["👀VR", "❤️Реакции"]))
    await state.set_state(CurrentFunction.filtering_posts_by_type)


@router.message(CurrentFunction.filtering_posts_by_type)
async def set_filter_by_type(message, state):
    if 'реакц' in message.text.lower():
        metric = "reactions"
    if any(word in message.text.lower() for word in ['просмотры', 'vr']):
        metric = "vr"
    await state.update_data(metric=metric)
    await message.answer("Тебе нужны посты со ссылками или с текстом?",
                         reply_markup=make_row_keyboard(['🔗Ссылки', '📄Текст', 'Все посты']))
    await state.set_state(CurrentFunction.filtering_posts_by_words)


@router.message(CurrentFunction.filtering_posts_by_words)
async def set_filter_by_words(message, state):
    global post_type
    if 'ссылки' in message.text.lower():
        post_type = 'links'
    elif 'текст' in message.text.lower():
        post_type = 'text_type'
    elif 'все' in message.text.lower():
        post_type = False
    await message.answer("Введи слова/словосочетания, которые должны содержаться в посте, через ;",
                         reply_markup=make_row_keyboard(['Без фильтра']))
    await state.set_state(CurrentFunction.showing_posts)


@router.message(CurrentFunction.showing_posts)
async def show_posts(message, state):
    global post_type
    if 'без фильтра' in message.text.lower():
        word_filter = None
    else:
        word_filter = message.text.split(';')
    user_data = await state.get_data()
    post_list = await tools.sorted_posts(user_data['post_dict'], order_by=user_data['metric'],
                                         post_type=post_type, word_filter=word_filter)
    print('post_list', len(post_list))
    for post in post_list[: min(len(post_list), 10)]:
        await message.answer(
            "Ссылка на пост: " + f"https://t.me/{post['channel_name']}/{post['id']}" + "\n" +
            "Реакций: " + str(post['reactions']) + "\n" + "Ссылки:" + '\n'.join(post['links']) + "\n",
            reply_markup=post_from_post_button(post['channel_name'], post['id']))
    await state.set_state(state=None)
    await choose_action(message)


async def choose_action(message):
    await message.answer("Что сделать?",
                         reply_markup=make_row_keyboard(["✍️Сделать пост", "🏆Топ постов", "♻️Обновить список каналов"]))


async def parsing_channels(message, state):
    user_data = await state.get_data()
    channels = user_data['channels']
    limit = user_data['limit']
    await message.answer("Начал парсить...",
                         parse_mode="Markdown")
    post_dict = await tools.get_posts(channels, limit=limit)
    await state.update_data(post_dict=post_dict)
    await state.set_state(state=None)
    if not user_data['updating_channels']:
        scheduler.add_job(update_posts, "interval", hours=24, args=(state,))
        await state.update_data(updating_channels=True)


@router.message(F.text.lower() == "✍️сделать пост")
async def link_for_post(message, state):
    await message.answer("Отправь ссылку на статью")
    await state.set_state(CurrentFunction.making_post)


@router.message(F.text.lower() == "♻️Обновить список каналов")
async def update_channels(message, state):
    await message.answer("Функция в разработке")
    await choose_action(message)
    # await state.set_state(CurrentFunction.making_post)


@router.message(CurrentFunction.making_post)
async def making_post(message: Message):
    global client
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
        article_summary = await tools.summarization(article_text)
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
            completion = client.chat.completions.create(model=model,
                                                        messages=messages,
                                                        )
        else:
            completion = client.chat.completions.create(model=model,
                                                        messages=messages,
                                                        )
        # completion.choices представляет собой список возможных вариантов ответов, сгенерированных моделью чат-бота. Каждый вариант ответа содержит свойство message, которое представляет собой объект сообщения с двумя свойствами: role (роль отправителя) и content (содержание сообщения).
        # Мы берем первый (нулевой) элемент-первый вариант ответа, сгенерированный моделью.
        await message.answer("Пост сделан!")
        decoded_response = completion.choices[0].message.content.encode('utf-8').decode('utf-8')
        messages.append({"role": "assistant",
                         "content": decoded_response})
        await message.answer(decoded_response,
                             parse_mode='Markdown')
    # Если слишком часто отправляем запросы, он начинает ругаться
    except openai.RateLimitError:
        await message.answer('Лимит по времени, напиши еще раз')
    except openai.InternalServerError:
        await message.answer('Сервера OpenAI недоступны, повтори позже')


async def update_posts(state):
    user_data = await state.get_data()
    post_dict = user_data['post_dict']
    channels = user_data['channels']
    post_dict = await tools.updated_posts(channels, post_dict)
    await state.update_data(post_dict=post_dict)


@router.callback_query(F.data.startswith("post_from_post"))
async def get_post_from_post(callback, state):

    global client
    global messages
    model = "gpt-3.5-turbo"
    message = callback.message
    messages = []
    channel = callback.data.split('.')[1]
    post_id = int(callback.data.split('.')[2])
    user_data = await state.get_data()
    post_text = user_data['post_dict'][channel][post_id]['text']
    prompt = "Представь, что ты копирайтер телеграм канала. Тебе показался интересным " \
             "и полезным пост с другого канала @{0}, и ты хочешь рассказать он нем" \
             "своим подписчикам (но не пересылать полностью). Упомяни коротко, " \
             "о чем он, почему может быть полезен, и оставь тег канала, с которого " \
             "был взят этот пост. Вот сам пост, он в разметке Markdown: {1}".format(channel, post_text)


    messages.append(
        {"role": "assistant",
         "content": prompt})  # assistant - значит он сохраняет контекст."role" (роль отправителя - "system", "user" или "assistant") и "content" (содержание сообщения).

    try:
        await message.answer("Делаем пост...")
        await callback.answer()
        completion = client.chat.completions.create(model=model,
                                                    messages=messages,
                                                    )
        await message.answer("Пост сделан!")
        decoded_response = completion.choices[0].message.content.encode('utf-8').decode('utf-8')
        messages.append({"role": "assistant",
                         "content": decoded_response})
        await message.answer(decoded_response)
    # Если слишком часто отправляем запросы, он начинает ругаться
    except openai.RateLimitError:
        await message.answer('Лимит по времени, напиши еще раз')
    except openai.InternalServerError:
        await message.answer('Сервера OpenAI недоступны, повтори позже')

    await state.set_state(CurrentFunction.editing_post)
