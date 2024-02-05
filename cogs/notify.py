from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from traceback import format_exception as fmt_exc


class Notify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description="バーチャルコンテストの結果を表示します。")
    @app_commands.describe(vcon_id="バーチャルコンテストのID")
    async def send_vcon_standings(self, ctx: commands.Context, vcon_id: str):
        # ブラウザのウィンドウを表すオブジェクト"driver"を作成
        await ctx.reply("結果")
        channel = ctx.channel
        options = Options()
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)

        # サイトにアクセス
        url = (
            f"https://kenkoooo.com/atcoder/#/contest/show/{vcon_id}?activeTab=Standings"
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
        with open("image/screenshot.png", "wb") as f:
            f.write(png)

        # ユーザー名、パフォーマンスを取得
        results = {}
        # 表の全てのデータを取得
        trs = standings.find_elements(By.TAG_NAME, "tr")
        # 最初、最後の行は無視
        for i in range(1, len(trs) - 1):
            ths = trs[i].find_elements(By.TAG_NAME, "th")
            tds = trs[i].find_elements(By.TAG_NAME, "td")
            results[ths[1].text] = tds[-1].text

        print(results)
        await channel.send(file=discord.File("image/screenshot.png"))
        driver.quit()


async def setup(bot):
    await bot.add_cog(Notify(bot))
