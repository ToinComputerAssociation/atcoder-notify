from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import asyncio
import aiohttp
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from traceback import format_exception as fmt_exc
import datetime
import heapq
from typing import TypedDict, NotRequired
import json
import rating

class History(TypedDict):
    vcon_name : str
    vcon_id : int
    end_time : int
    performance : float
    new_rating : float
    old_rating : float

class User(TypedDict):
    discord_id: int
    rating : float
    join_count : int
    histories: list[History]


class Notify(commands.Cog):
    #通知予定のバーチャルコンテスト
    vcon_schedule = []
    #レーティング反映済みのコンテスト
    vcons : list[dict]
    #ユーザー情報
    users : dict[str, User]
    NOTICE_CHANNEL_ID = 1200215788678815834
    #testchannel
    #NOTICE_CHANNEL_ID = 911924965501206581

    def __init__(self, bot):
        self.bot = bot
        heapq.heapify(self.vcon_schedule)

    async def cog_load(self):
        "コグのロード時の動作"
        with open("data/users.json", mode="r") as f:
            self.users = json.load(f)
        with open("data/vcons.json", mode="r") as f:
            self.vcons = json.load(f)
        self.check_schedule.start()

    async def cog_unload(self):
        "コグのアンロード時の動作"
        self.check_schedule.cancel()
        self.save_data()

    @commands.Cog.listener()
    async def on_message(self, message):
        #TCAbotから朝練を取得
        if "今日の朝練:" in message.content:
            vcon_id = message.content.split('/')[-1]
            await self.push_vcon(vcon_id)
        
    @tasks.loop(seconds=1)
    async def check_schedule(self):
        if len(self.vcon_schedule) == 0:
            return
        first = heapq.heappop(self.vcon_schedule)
        if first[0] <= time.time():
            vcon = first[1]
            await self.get_vcon_standings(vcon["info"]["id"])
            
            channel = self.bot.get_channel(self.NOTICE_CHANNEL_ID)
            button = discord.ui.Button(label="更新",style=discord.ButtonStyle.primary,custom_id=f'update_vcon_standings,{vcon["info"]["id"]}')
            view = discord.ui.View()
            view.add_item(button)
            await channel.send(content=f'**「[{vcon["info"]["title"]}](https://kenkoooo.com/atcoder/#/contest/show/{vcon["info"]["id"]})」の結果**({"{0:%Y/%m/%d %H:%M}".format(datetime.datetime.now())} 時点)', file=discord.File("image/vcon.png"), view=view)
        else:
            heapq.heappush(self.vcon_schedule, first)

    def get_user_from_discord(self, discord_id: int):
        for user_id in self.users.keys():
            if self.users[user_id]["discord_id"] == discord_id:
                return user_id
        return False

    async def get_vcon(self, vcon_id: str):
        vcon_url = f"https://kenkoooo.com/atcoder/internal-api/contest/get/{vcon_id}"
        async with aiohttp.ClientSession(loop=self.bot.loop) as session:
            response = await session.get(vcon_url)
            jsonData = await response.json()
            return jsonData
    
    async def push_vcon(self, vcon_id: str):
        #予定にバーチャルコンテストを追加
        vcon = await self.get_vcon(vcon_id)
        endtime = vcon["info"]["start_epoch_second"] + vcon["info"]["duration_second"]
        heapq.heappush(self.vcon_schedule, (endtime, vcon))

    @commands.hybrid_command(description="バーチャルコンテストの結果を表示します。")
    @app_commands.describe(vcon_id="バーチャルコンテストのID")
    async def push_vcon_hand(self, ctx: commands.Context, vcon_id: str):
        #予定にバーチャルコンテストを追加（手動）
        vcon = await self.get_vcon(vcon_id)
        endtime = vcon["info"]["start_epoch_second"] + vcon["info"]["duration_second"]
        await ctx.reply(f'予定に「[{vcon["info"]["title"]}](https://kenkoooo.com/atcoder/#/contest/show/{vcon["info"]["id"]})」を追加しました。')
        heapq.heappush(self.vcon_schedule, (endtime, vcon))
        
    @commands.hybrid_command(description="朝練にratedで参加します")
    @app_commands.describe(user_id="AtCoderのユーザーID")
    async def register(self, ctx: commands.Context, user_id: str):
        if user_id in self.users:
            return await ctx.reply("このAtCoderユーザーは登録済みです。")

        self.users[user_id] = {"discord_id": ctx.author.id, "rating": 0,  "join_count" : 0, "histories" : []}
        await ctx.reply("登録しました。")

    @commands.hybrid_command(description="レーティングを更新します")
    @app_commands.describe(vcon_id="バーチャルコンテストのID")
    async def push_button(self, ctx: commands.Context, vcon_id: str):
        vcon = await self.get_vcon(vcon_id)
        button_update = discord.ui.Button(label="更新",style=discord.ButtonStyle.primary,custom_id=f'update_rating,{vcon_id}')
        button_cancel = discord.ui.Button(label="キャンセル",style=discord.ButtonStyle.primary,custom_id=f'cancel')
        view = discord.ui.View()
        view.add_item(button_update)
        view.add_item(button_cancel)
        await ctx.reply(f'**「[{vcon["info"]["title"]}](https://kenkoooo.com/atcoder/#/contest/show/{vcon["info"]["id"]})」の結果をレーティングに反映させます。\n全ての提出が順位表に反映されていることを確認してください。**', view=view)

    async def send_rating_fluctuation(self, vcon_id : str):
        messages = []
        channel = self.bot.get_channel(self.NOTICE_CHANNEL_ID)
        vcons = [contest for contest in self.vcons if contest["info"]["id"] == vcon_id]
        if(len(vcons) == 0):
            await channel.send('コンテストが存在しません')
        vcon = vcons[0]
        messages.append(f'「[{vcon["info"]["title"]}](https://kenkoooo.com/atcoder/#/contest/show/{vcon["info"]["id"]})」のレーティング変動')
        for user_id in self.users.keys():
            for history in self.users[user_id]["histories"]:
                if history["vcon_id"] != vcon_id:
                    continue
                old_rating = history["old_rating"]
                new_rating = history["new_rating"]
                difference = new_rating - old_rating
                message = f"{user_id}: {old_rating} -> {new_rating}({'{:+}'.format(difference)})"
                messages.append(message)
        await channel.send('\n'.join(messages))

        


    async def get_vcon_standings(self, vcon_id : str):
        # ブラウザのウィンドウを表すオブジェクト"driver"を作成
        options = Options()
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)

        # サイトにアクセス
        url = (
            f'https://kenkoooo.com/atcoder/#/contest/show/{vcon_id}?activeTab=Standings'
        )
        driver.get(url)
        await asyncio.sleep(1)

        # レートを表示
        driver.find_element(
            By.XPATH,
            '//*[@id="root"]/div/div[2]/div[6]/div[1]/div/form/div/div[2]/label',
        ).click()
        await asyncio.sleep(1)

        # ウィンドウの大きさを変更
        w = driver.execute_script("return document.body.scrollWidth")
        # h = driver.execute_script('return document.body.scrollHeight')
        adjustment = 20  # 幅微調整
        driver.set_window_size(w + adjustment, 6400)

        # 順位表を取得
        standings = driver.find_element(
            By.XPATH, '//*[@id="root"]/div/div[2]/div[6]/div[2]/div/table[1]'
        )
        # 範囲を指定してスクリーンショットを撮る
        png = standings.screenshot_as_png
        # ファイルに保存
        with open("image/vcon.png", "wb") as f:
            f.write(png)
        
        driver.quit()

    async def get_vcon_results(self, vcon_id : str):
        # ブラウザのウィンドウを表すオブジェクト"driver"を作成
        options = Options()
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)

        # サイトにアクセス
        url = (
            f'https://kenkoooo.com/atcoder/#/contest/show/{vcon_id}?activeTab=Standings'
        )
        driver.get(url)
        await asyncio.sleep(3)

        # ウィンドウの大きさを変更
        w = driver.execute_script("return document.body.scrollWidth")
        # h = driver.execute_script('return document.body.scrollHeight')
        adjustment = 20  # 幅微調整
        driver.set_window_size(w + adjustment, 6400)

        # 順位表を取得
        standings = driver.find_element(
            By.XPATH, '//*[@id="root"]/div/div[2]/div[6]/div[2]/div/table[1]'
        )

        # ユーザー名、パフォーマンスを取得
        results = {}
        # 表の全てのデータを取得
        trs = standings.find_elements(By.TAG_NAME, "tr")
        # 最初、最後の行は無視
        for i in range(1, len(trs) - 1):
            ths = trs[i].find_elements(By.TAG_NAME, "th")
            tds = trs[i].find_elements(By.TAG_NAME, "td")
            results[ths[1].text] = int(tds[-1].text)
        
        driver.quit()

        return results

            
    async def update_rating(self, results : dict, vcon : dict):
        for user_id in self.users.keys():
            self.users[user_id]["join_count"] += 1
            #不参加のときのperformanceは0
            performance = results.get(user_id, 0)
            old_rating = self.users[user_id]["rating"]
            new_rating = rating.calc(old_rating, self.users[user_id]["join_count"], performance)
            self.users[user_id]["rating"] = new_rating
            self.users[user_id]["histories"].append({"vcon_name" : vcon["info"]["title"], "vcon_id" : vcon["info"]["id"], "endt_time" : vcon["info"]["start_epoch_second"] + vcon["info"]["duration_second"], "performance" : performance, "old_rating" : old_rating, "new_rating" : new_rating})


    @commands.Cog.listener()
    async def on_interaction(self, inter:discord.Interaction):
        try:
            if inter.data['component_type'] == 2:
                await self.on_button_click(inter)
            elif inter.data['component_type'] == 3:
                await self.on_dropdown(inter)
        except KeyError:
            pass

    async def on_button_click(self, inter:discord.Interaction):
        custom_id = inter.data["custom_id"]
        if "update_vcon_standings" in custom_id:
            await inter.response.send_message("更新中...",ephemeral=True)
            vcon = await self.get_vcon(custom_id.split(',')[-1])
            await self.get_vcon_standings(vcon["info"]["id"])
            channel = self.bot.get_channel(self.NOTICE_CHANNEL_ID)
            button = discord.ui.Button(label="更新",style=discord.ButtonStyle.primary,custom_id=f'update_vcon_standings,{vcon["info"]["id"]}')
            view = discord.ui.View()
            view.add_item(button)
            await inter.message.edit(content=f'**「[{vcon["info"]["title"]}](https://kenkoooo.com/atcoder/#/contest/show/{vcon["info"]["id"]})」の結果**({"{0:%Y/%m/%d %H:%M}".format(datetime.datetime.now())} 時点)', attachments=[discord.File("image/vcon.png")], view=view)
            await inter.delete_original_response()
        if "update_rating" in custom_id:
            vcon = await self.get_vcon(custom_id.split(',')[-1])
            if vcon in self.vcons:
                await inter.response.send_message("このコンテストは反映済みです。", ephemeral=True)
                return
            await inter.message.delete()
            await inter.response.send_message("更新中...",ephemeral=True)
            results = await self.get_vcon_results(vcon["info"]["id"])
            print(results)
            await self.update_rating(results, vcon)
            self.vcons.append(vcon)
            await inter.delete_original_response()
            channel = self.bot.get_channel(self.NOTICE_CHANNEL_ID)
            await channel.send("ボタンをおしました。")
            await self.send_rating_fluctuation(vcon["info"]["id"])
        if "cancel" == custom_id:
            #await inter.response.defer()
            await inter.message.delete()
            #await inter.delete_original_response()
            
            

    def save_data(self):
        print("Saving Data...")
        with open("data/users.json", mode="w") as f:
            json.dump(self.users, f)
        with open("data/vcons.json", mode="w") as f:
            json.dump(self.vcons, f)
        # バックアップをとる。
        today = datetime.date.today()
        with open(f"data/backup/{today.strftime(r'%Y%m%d')}_users.json", mode="w") as f:
            json.dump(self.users, f)
        with open(f"data/backup/{today.strftime(r'%Y%m%d')}_vcons.json", mode="w") as f:
            json.dump(self.vcons, f)
        weekago = today - datetime.timedelta(days=30)
        # 30日で自動削除
        if os.path.isfile(f"data/backup/{weekago.strftime(r'%Y%m%d')}_users.json"):
            os.remove(f"data/backup/{weekago.strftime(r'%Y%m%d')}_users.json")
        if os.path.isfile(f"data/backup/{weekago.strftime(r'%Y%m%d')}_vcons.json"):
            os.remove(f"data/backup/{weekago.strftime(r'%Y%m%d')}_vcons.json")



async def setup(bot):
    await bot.add_cog(Notify(bot))
