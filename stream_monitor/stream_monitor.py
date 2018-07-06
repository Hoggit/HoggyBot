import asyncio
import aiohttp
import discord
import json
import os
from .utils import checks
from .utils.dataIO import fileIO
from discord.ext import commands

class StreamMonitor:
    """
    Track stream status
    """

    def __init__(self, bot, dataFile):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.dataFile = dataFile
        self.data = fileIO(dataFile, 'load')
        asyncio.ensure_future(self.start_monitor())

    async def start_monitor(self):
        self.bot.wait_until_ready()
        asyncio.ensure_future(self._poll())


    def makeRequest(self, data):
        url="https://api.twitch.tv/kraken/streams?community_id={}".format(data['community'])
        headers={'Accept': 'application/vnd.twitchtv.v5+json', 'Client-ID': data['clientId']}
        return self.session.get(url, headers=headers)


    async def _poll(self):
        try:
            if 'channel' not in self.data:
                log("No channel configured for alerts. Skipping poll")
                await asyncio.sleep(600)
                asyncio.ensure_future(self._poll())
                return
            channel_id = self.data['channel']
            message_id = self.data['message']
            response = await self.makeRequest(self.data)
            responseTxt = await response.text()
            log("Got response text: {}".format(responseTxt))
            channel = self.bot.get_channel(channel_id)
            message = await self.bot.get_message(channel, message_id)
            log("Sending update")
            await self.bot.edit_message(message, responseTxt)
        finally:
            await asyncio.sleep(60)
            asyncio.ensure_future(self._poll())


    def save_data(self, data):
        fileIO(self.dataFile, 'save', data)

    @commands.group(name="streammon", pass_context=True, no_pm=True, invoke_without_command=True)
    async def _streammon(self, ctx):
        """Stream monitor config"""
        await self.bot.send_cmd_help(ctx)

    @_streammon.command(name="community", no_pm=True)
    async def _community(self, community_id):
        """Adds a community to track on twitch.tv. Must be the community _id_"""
        self.data['community'] = community_id
        self.save_data(self.data)
        await self.bot.say("Tracking community with id: {}".format(community_id))

    @_streammon.command(name="channel", no_pm=True)
    async def _channel(self, channel: discord.Channel):
        self.data['channel'] = channel.id
        await self.bot.say("Set stream alerting channel to {}".format(channel.name))
        msg = await self.bot.send_message(channel, "Stream Alerts Enabled")
        self.data['message'] = msg.id
        self.save_data(self.data)

    @_streammon.command(name="clientid", no_pm=True)
    async def _setClientId(self, clientId):
        self.data['clientId'] = clientId
        self.save_data(self.data)
        await self.bot.say("Updated client Id")


def log(s):
    print("StreamMonitor: {}".format(s))

def setup(bot):
    if not os.path.exists('data/streammonitor'):
        log("Creating data/streammonitor folder")
        os.makedirs('data/streammonitor')

    f = 'data/streammonitor/data.json'
    if not fileIO(f, "check"):
        log("Creating empty data.json")
        fileIO(f, "save", {})

    bot.add_cog(StreamMonitor(bot, f))
