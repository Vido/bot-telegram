# -*- coding: utf-8 -*-

import os
import requests
from bs4 import BeautifulSoup
from functools import lru_cache
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
from cachetools import TTLCache, cached

from decouple import config

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


API_KEY = config('API_KEY')

class Commodity:
    """
    Class that represent a commodity
    """

    def __init__(self,
                 name,
                 due_date,
                 previous_adjustment_price,
                 current_adjustment_price,
                 variation,
                 contract_adjustment_amount):
        self._name = name
        self.due_date = due_date
        self.previous_adjustment_price = previous_adjustment_price
        self.current_adjustment_price = current_adjustment_price
        self.variation = variation
        self.contract_adjustment_amount = contract_adjustment_amount

    @property
    def name(self):
        return self._name

    @property
    def acronym(self):
        """Extract acronym from name"""
        return self.name.split('-')[0].strip() if '-' in self.name else self.name


@cached(cache=TTLCache(maxsize=2048, ttl=6000))
def get_all_data():
    """
    Retrieve all information and parse to list of commodities
    """
    bmf_url = 'http://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-ajustes-do-pregao-ptBR.asp'
    response = requests.get(bmf_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    results = soup.find(id='tblDadosAjustes').find('tbody')
    name = ''
    commodities = []
    for tr in results.children:
        if hasattr(tr, 'children'):
            elements = [el for el in tr.children if '\n' != el]
            name = elements[0].text if elements[0].text != '' else name
            commodity = Commodity(name.strip(),
                                  elements[1].text.strip(),
                                  elements[2].text.strip(),
                                  elements[3].text.strip(),
                                  elements[4].text.strip(),
                                  elements[5].text.strip())
            commodities.append(commodity)
    return commodities


def list_all(update, context):
    """
    List all commodities in chat
    """
    commodities = get_all_data()
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="A lista de mercadorias é:")
    all_titles = sorted(list(set([c.name for c in commodities])))
    for title in all_titles:
        context.bot.send_message(chat_id=update.effective_chat.id, text=title)


def help(update, context):
    """
    Return the manual of utilization
    """
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Você pode digitar /listar para listar todos as mercadorias ou ...')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='digitar /info CODIGOVENCIMENTO  para obter o valor.')
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='exemplo:  /info VALEOG20')


def info(update, context):
    """
    Return the commodity information
    """
    commodities = get_all_data()
    arg = context.args[0].upper()
    commodities = list(filter(lambda c: c.acronym ==
                              arg[:-3] and c.due_date == arg[-3:], commodities))
    if len(commodities) == 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=f'Não foi encontrado mercadoria com o código: {arg[:-3]} e vencimento {arg[-3:]}')

    for commodity in commodities:
        text = f'Mercadoria: {commodity.name}\n' \
        f'Vencimento: {commodity.due_date}\n' \
        f'Preço de ajuste anterior: {commodity.previous_adjustment_price}\n' \
        f'Preço de ajuste Atual: {commodity.current_adjustment_price}\n' \
        f'Variação: {commodity.variation}\n' \
        f'Valor do ajuste por contrato (R$): {commodity.contract_adjustment_amount}'

        context.bot.send_message(
            chat_id=update.effective_chat.id, text=text)

"""
Create all events
"""


def main():
    updater = Updater(API_KEY, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', help))
    dp.add_handler(CommandHandler('listar', list_all))
    dp.add_handler(CommandHandler('info', info))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
