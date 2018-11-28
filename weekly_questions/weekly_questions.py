import praw
import asyncio
import discord
import re
import os
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks


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
        if "ignored_usernames" not in self.data:
            self.data["ignored_usernames"] = []
        self.killPoll = False
        asyncio.ensure_future(self.poll())

    def __unload(self):
        self.killPoll = True

    def reddit(self):
        if "clientid" not in self.data["reddit"] or "clientsecret" not in self.data["reddit"]:
            raise RedditNotConfigured()
        clientid = self.data["reddit"]["clientid"]
        clientsecret = self.data["reddit"]["clientsecret"]
        return praw.Reddit(client_id=clientid, client_secret=clientsecret, user_agent='praw Hoggybot')

    def save_data(self, data):
        dataIO.save_json(self.data_file, data)


    def weekly_thread(self):
        subreddit = self.reddit().subreddit('hoggit')
        posts = (post for post in subreddit.hot(limit=2) if post.stickied)
        for post in posts:
            if re.search("^Tuesday Noob Questions", post.title):
                return post
        return None

    async def weekly_questions_comments(self, last_utc_check):
        if not last_utc_check:
            last_utc_check = 0
        thread = self.weekly_thread()
        thread.comment_sort = 'new'
        comments = [c for c in thread.comments if c.created_utc > last_utc_check]
        return comments

    async def say_comments(self, comments):
        if "channel" not in self.data:
            log("Could not post {} comments to a channel, as no channel is configured".format(len(comments)))
            return
        channel_id = self.data["channel"]
        log("looking up channel with id: {}".format(channel_id))
        chan = self.bot.get_channel(channel_id)
        if not chan:
            log("Can't find channel with id: {}".format(channel_id))
            return
        for comment in comments:
            if comment.author.name not in self.data["ignored_usernames"]:
                embed = discord.Embed()
                question = comment.body[:75] + "..." if len(comment.body) > 75 else comment.body
                embed.add_field(name="User", value=comment.author.name, inline=False)
                embed.add_field(name="Question", value=question, inline=False)
                embed.add_field(name="Link", value="https://reddit.com{}".format(comment.permalink), inline=False)
                await self.bot.send_message(chan, embed=embed)

    async def poll(self):
        try:
            await self.bot.wait_until_ready()
            last_utc = 0
            if "last_utc_check" in self.data["reddit"]:
                last_utc = self.data["reddit"]["last_utc_check"]
            comments = await self.weekly_questions_comments(last_utc)
            if len(comments) > 0:
                last_comment_utc = max(c.created_utc for c in comments)
                self.data["reddit"]["last_utc_check"] = last_comment_utc
                self.save_data(self.data)
                await self.say_comments(comments)
            log("Poll completed. Found {} comments".format(len(comments)))
        except RedditNotConfigured:
            log("Reddit not configured. Skipping poll")
        finally:
            if self.killPoll:
                log("Killswitch engaged. Stopping polling")
                return
            await asyncio.sleep(10)
            asyncio.ensure_future(self.poll())

    @commands.group(name="weeklyquestions", pass_context=True, invoke_without_command=True)
    async def _weeklyquestions(self, ctx):
        """
        Lists the current weekly questions thread
        """
        post = self.weekly_thread()
        if post:
            await self.bot.say("This week's question thread: http://reddit.com{}".format(post.permalink))
            return

        await self.bot.say("Couldn't find this week's question thread. Is it stickied?")
        return

    @_weeklyquestions.command(name="ignore")
    @checks.is_owner()
    async def _ignore_user(self, user:str):
        """
        Ignores a username from the weekly threads.
        Commands by these users are no longer displayed
        """
        if "ignored_usernames" not in self.data:
            self.data["ignored_usernames"] = []
        self.data["ignored_usernames"].append(user)
        self.save_data(self.data)
        await self.bot.say("Added {} to ignored list".format(user))

    @_weeklyquestions.command(name="channel")
    @checks.is_owner()
    async def _set_channel(self, chan: discord.Channel):
        """
        Sets the channel to send the questions to
        """
        self.data["channel"] = chan.id
        self.save_data(self.data)
        await self.bot.say("Set the question channel to {}".format(chan.name))


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

    @_reddit.command(name="clientsecret", pass_context=True)
    @checks.is_owner()
    async def _clientsecret(self, ctx, clientsecret: str):
        if "reddit" not in self.data:
            self.data["reddit"] = {}
        self.data["reddit"]["clientsecret"] = clientsecret
        self.save_data(self.data)
        await self.bot.say("Reddit Client Secret set")

def setup(bot):
    data_dir = "data/weekly_questions"
    data_file = "{}/data.json".format(data_dir)
    if not os.path.exists(data_dir):
        print("WeeklyQuestions: Creating {} folder...".format(data_dir))
        os.makedirs(data_dir)
    if not dataIO.is_valid_json(data_file):
        dataIO.save_json(data_file, {})

    bot.add_cog(HoggitWeeklyQuestions(bot, data_file))

def log(msg):
    print("[WeeklyQuestions]--{}".format(msg))
    return
