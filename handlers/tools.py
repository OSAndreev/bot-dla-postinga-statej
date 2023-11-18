from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
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
    post_list = []
    for channel_username in channels:
        posts, participants = await get_channel_posts(api_id, api_hash, channel_username, limit=limit)
        print([post.views for post in posts])
        for post in posts:
            post_text = post.text
            post_reactions = None
            if post.reactions:
                post_reactions = sum([react.count for react in post.reactions.results])
            post_views = post.views
            if post_views:
                post_list.append({'text': post_text, 'reactions': post_reactions,
                                  'vr': post_views/participants, 'channel_name': channel_username, 'id': post.id})
    return sorted(post_list, key=lambda post: post['vr'], reverse=True)

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
