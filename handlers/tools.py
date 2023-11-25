from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import MessageEntityTextUrl

import openai
import asyncio

openai.api_key = "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"
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
        posts, participants = await get_channel_posts(api_id, api_hash, channel_username, limit=limit)

        for post in posts:
            text_type = False
            link_type = False
            links = []
            for url_entity, inner_text in post.get_entities_text(MessageEntityTextUrl):
                url = url_entity.url
                links.append(url)
                print(url)

            post_text = post.text
            if post_text and len(post_text) > 3000:
                text_type = True
            if links:
                link_type = True
            post_reactions = None
            if post.reactions:
                post_reactions = sum([react.count for react in post.reactions.results])
            post_views = post.views
            if post_views and (text_type or link_type):
                if channel_username in post_dict:
                    post_dict[channel_username][post.id] = {'text': post_text, 'reactions': post_reactions,
                                                    'vr': post_views/participants}
                else:
                    post_dict[channel_username] = {post.id:{'text': post_text, 'reactions': post_reactions,
                                                    'vr': post_views/participants }}
                post_dict[channel_username][post.id]['links'] = links
                post_dict[channel_username][post.id]['text_type'] = text_type
                post_dict[channel_username][post.id]['link_type'] = link_type
    return post_dict

async def summarization(article_text):
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


async def updated_posts(channels, post_dict, limit=50):
    for channel in channels:
        channel_post_dict = await get_posts([channel], limit=limit)
        for post_id in channel_post_dict[channel].keys():
            post_dict[channel][post_id] = channel_post_dict[channel][post_id]
    return post_dict


async def sorted_posts(post_dict, post_type=False, order_by='vr'):
    post_list = []
    for channel in post_dict:
        for post in post_dict[channel]:
            if (post_type is False) or post_dict[channel][post][post_type]:
                curr_post_dict = {'channel_name': channel,  'id': post}
                for key in post_dict[channel][post].keys():
                    curr_post_dict[key] = post_dict[channel][post][key]
                post_list.append(curr_post_dict)
    return sorted(post_list, key=lambda post: post[order_by] if post[order_by] else 0, reverse=True)




