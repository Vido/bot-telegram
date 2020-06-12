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
    all_titles = sorted(list(set([c.name for c in commodities])))
    context.bot.send_message(chat_id=update.effective_chat.id,
        text='\n'.join(all_titles))


def help(update, context):
    """
    Return the manual of utilization
    """
    text = 'Você pode digitar:\n' \
    '/listar - lista todos os contratos BM&F\n' \
    '/ajuste CODIGOVENCIMENTO - para obter o valor do ajuste.'

    context.bot.send_message(
        chat_id=update.effective_chat.id, text=text)


def ajuste(update, context):
    """
    Return the commodity information
    """

    if not context.args:
        text = '/ajuste CODIGOVENCIMENTO - para obter o valor do ajuste. \n' \
        'exemplo: /ajuste DOLN20 (Dolar vencimento 01/07/2020)' 
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        return

    arg = context.args[0].upper()
    commodities = get_all_data()
    commodities = list(filter(lambda c: c.acronym ==
                            arg[:-3] and c.due_date == arg[-3:], commodities))

    if len(commodities) == 0:
        text=f'Não foi encontrado contrato com o código: {arg[:-3]} e vencimento {arg[-3:]}'
        if arg in set(['OZ1D', 'OZ2D', 'OZ3D']):
            text=f'OZ1D, OZ2D e OZ3D são mercadorias Disponíveis. Os contratos futuros são OZ1 + código do vencimento'

        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

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
    #dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('listar', list_all))
    dp.add_handler(CommandHandler('ajuste', ajuste))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
