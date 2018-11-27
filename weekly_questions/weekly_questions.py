import praw
import asyncio
import discord
from discord.ext import commands
from .utils.dataIO import dataIO


class RedditNotConfigured(Exception):
    def __init__(self):
        """
        Used for when reddit has not been configured on the bot yet
        """
        return

class HoggitWeeklyQuestions:
    """
    Relays new top-level comments from the stickied questions thread into a channel
    on discord.
    """

    def __init__(self, bot, data_file):
        self.bot = bot
        self.data_file = data_file
        self.data = dataIO.load_json(data_file)

    def reddit():
        if self.data["reddit"]["client_id"]:

    def save_data(self, data):
        fileIO(self.data_file, 'save', data)


    @commands.group(name="weeklyquestions", pass_context=True, invoke_without_command=True)
    async def _weeklyquestions(self, ctx):
        """
        Lists the current weekly questions thread
        """
        return

    @commands.group(name="reddit")
    async def _reddit(self):
        return

    @_reddit.command(name="clientid", pass_context=True)
    @checks.is_owner()
    async def _clientid(self, ctx, clientid: str):
        if "reddit" not in self.data:
            self.data["reddit"] = {}
        self.data["reddit"]["clientid"] = clientid
        self.save_data(self.data)
        await self.bot.say("Reddit Client ID set")

    @_reddit.command(name="clientid", pass_context=True)
    @checks.is_owner()
    async def _clientsecret(self, ctx, clientsecret: str):
        if "reddit" not in self.data:
            self.data["reddit"] = {}
        self.data["reddit"]["clientsecret"] = clientsecret
        self.save_data(self.data)
        await self.bot.say("Reddit Client Secret set")





def setup(bot):
    data_dir = "data/weekly_questions"
    if not os.path.exists(data_dir):
        print("WeeklyQuestions: Creating {} folder...".format(data_dir))
        os.makedirs(data_dir)

    data_file = "{}/data.json".format(data_dir)
    bot.add_cog(HoggitWeeklyQuestions(bot, data_file))
