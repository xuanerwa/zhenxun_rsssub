import asyncio

from nonebot import get_driver, logger
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters.onebot.v11 import Bot as OneBot

from . import commands as commands
from .host_adapter import remember_bot
from .plugin_meta import __plugin_meta__ as __plugin_meta__
from .repository_db import DB_FILE
from .rss import RSS
from .scheduler import create_rss_update_job

driver = get_driver()
_rss_jobs_initialized = False
_rss_startup_lock: asyncio.Lock | None = None


def _get_startup_lock() -> asyncio.Lock:
    global _rss_startup_lock
    if _rss_startup_lock is None:
        _rss_startup_lock = asyncio.Lock()
    return _rss_startup_lock


async def _initialize_rss_jobs(bot: OneBot | None = None) -> None:
    """Initialize RSS jobs once without depending on OneBot meta events."""
    global _rss_jobs_initialized
    if bot is not None:
        remember_bot(bot)

    async with _get_startup_lock():
        if _rss_jobs_initialized:
            return

        logger.info(f"加载RSS数据文件: {DB_FILE}")
        rss_list = RSS.load_rss_data()

        if len(rss_list) == 0:
            logger.warning("尚无订阅数据，请使用 真寻帮助 订阅姬 查看使用方法")
        else:
            logger.info(f"已加载 {len(rss_list)} 项订阅数据")

        logger.info("启动检查订阅更新定时任务")
        await asyncio.gather(
            *[
                create_rss_update_job(rss, run_immediately=False)
                for rss in rss_list
                if not rss.stop
            ]
        )
        _rss_jobs_initialized = True
        logger.success("初始化完成")


@driver.on_startup
async def startup_handler() -> None:
    """Initialize scheduled RSS jobs when the driver starts."""
    await _initialize_rss_jobs()


@driver.on_bot_connect
async def bot_connect_handler(bot: BaseBot) -> None:
    """Remember OneBot instances for scheduled deliveries."""
    if not isinstance(bot, OneBot):
        return
    await _initialize_rss_jobs(bot)
