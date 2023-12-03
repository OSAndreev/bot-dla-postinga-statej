from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import MessageEntityTextUrl
import httpx
import openai
import asyncio

client = openai.OpenAI(
    api_key='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',
    http_client=httpx.Client(
          proxies="socks5://andreevos22:MJkXWdZjik@166.1.10.179:50101"
    ),
)
async def get_channel_posts(api_id, api_hash, channel_username, limit=2):
    async with TelegramClient('session_name', api_id, api_hash) as client:
        await client.start()
        channel = await client.get_entity(channel_username)
        channel_full_info = await client(GetFullChannelRequest(channel=channel))
        posts = await client.get_messages(channel, limit=limit)
        participants = channel_full_info.full_chat.participants_count
        await client.disconnect()
    return posts, participants

async def get_posts(channels: list, limit=1):
    api_id = '22526632'
    api_hash = 'a2adec3a58f237733ab5521b5f75337b'
    post_dict = dict()

    for channel_username in channels:
        try:
            posts, participants = await get_channel_posts(api_id, api_hash, channel_username, limit=limit)
            print('колво постов парсера', len(posts))
            for post in posts:
                text_type = False
                link_type = False
                links = []
                for url_entity, inner_text in post.get_entities_text(MessageEntityTextUrl):
                    url = url_entity.url
                    links.append(url)


                post_text = post.text
                if post_text and len(post_text) > 3000:
                    text_type = True
                if links:
                    link_type = True
                post_reactions = None
                if post.reactions:
                    post_reactions = sum([react.count for react in post.reactions.results])
                post_views = post.views
                if post_views:
                    if channel_username in post_dict:
                        post_dict[channel_username][post.id] = {'text': post_text, 'reactions': post_reactions,
                                                        'vr': post_views/participants}
                    else:
                        post_dict[channel_username] = {post.id:{'text': post_text, 'reactions': post_reactions,
                                                        'vr': post_views/participants }}
                    post_dict[channel_username][post.id]['links'] = links
                    post_dict[channel_username][post.id]['text_type'] = text_type
                    post_dict[channel_username][post.id]['link_type'] = link_type
        except ValueError:
            print(channel_username)
        for channel, posts in post_dict.items():
            print(len(posts.items()))
    return post_dict

async def summarization(article_text):
    global client
    model = "gpt-3.5-turbo-1106"
    sum_messages = []
    prompt = 'Я отправлю тебе статью на русском языке. Тебе нужно будет сделать ее краткую версию,минимальная длина которой 100 токенов, а максимальная длина не больше 300 токенов. Вот статья:'
    sum_messages.append(
        {"role": "assistant",
         "content": prompt + article_text})
    completion = client.chat.completions.create(model=model,
                                              messages=sum_messages)
    # except openai.InvalidRequestError:
    #     completion = openai.ChatCompletion.create(model=model,
    #                                               messages=sum_messages[:7000],
    #                                               )

    summary = completion.choices[0].message.content.encode('utf-8').decode('utf-8')
    return summary


async def updated_posts(channels, post_dict, limit=50):
    for channel in channels:
        channel_post_dict = await get_posts([channel], limit=limit)
        for post_id in channel_post_dict[channel].keys():
            post_dict[channel][post_id] = channel_post_dict[channel][post_id]
    return post_dict


async def sorted_posts(post_dict, post_type=False, order_by='vr', word_filter=None):
    post_list = []
    for channel in post_dict:
        for post in post_dict[channel]:
            if (post_type is False) or post_dict[channel][post][post_type]:
                if word_filter is None or \
                        all(word in post_dict[channel][post]['text'] for word in word_filter):
                    curr_post_dict = {'channel_name': channel,  'id': post}
                    for key in post_dict[channel][post].keys():
                        curr_post_dict[key] = post_dict[channel][post][key]
                    post_list.append(curr_post_dict)
    return sorted(post_list, key=lambda post: post[order_by] if post[order_by] else 0, reverse=True)


async def extract_channels(channels_string):
    channels_string = ''.join([i for i in channels_string.replace('https://t.me/', ' ').replace('/', ' ')
                               if i.isalpha() or i == '_' or i == ' '])
    channels_string = channels_string.split()
    extracted_channels = [i for i in channels_string if any(let.isalpha() for let in i)]
    extracted_channels = list(set(extracted_channels))
    print('каналы', extracted_channels)
    return extracted_channels




