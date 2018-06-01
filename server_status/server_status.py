import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
import aiohttp
from bs4 import BeautifulSoup

class DCSServerStatus:
    """
    Returns the status of your DCS server
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.base_url = "http://status.hoggitworld.com
