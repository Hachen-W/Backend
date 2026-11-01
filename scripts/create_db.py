import argparse
import asyncio

import app.models  # noqa: F401
from app.core.database import Base, engine


async def main(recreate: bool) -> None:
    async with engine.begin() as conn:
        if recreate:
            await conn.run_sync(Base.metadata.drop_all)
            print("Таблицы удалены")
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Таблицы созданы:", ", ".join(sorted(Base.metadata.tables)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Создание таблиц по метаданным моделей")
    parser.add_argument("--recreate", action="store_true", help="удалить и создать таблицы заново")
    asyncio.run(main(parser.parse_args().recreate))
