from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types


def make_row_keyboard(items):
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)


def post_from_post_button(channel, post_id):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Сделать пост",
        callback_data=f'post_from_post.{channel}.{post_id}')
    )
    return builder.as_markup()
