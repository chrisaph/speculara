"""Hosting contracts that do not require Docker or a desktop session."""
import asyncio,os,subprocess,sys
from pathlib import Path
from app import main


def test_configured_collector_volume_is_used_by_python_bridge(tmp_path):
    env={**os.environ,'SPECULARA_COLLECTOR_DATA_DIR':str(tmp_path/'session')}
    out=subprocess.check_output([sys.executable,'-c','from app.collector import DATA_DIR; print(DATA_DIR)'],env=env,text=True)
    assert Path(out.strip())==(tmp_path/'session').resolve()


def test_shutdown_closes_collection_and_login_in_order(monkeypatch):
    calls=[]
    async def cancel():calls.append('cancel')
    async def finish():calls.append('finish')
    monkeypatch.setattr(main.collector,'cancel_collection',cancel)
    monkeypatch.setattr(main.collector,'finish_login',finish)
    async def run():
        async with main.lifespan(main.app):assert calls==[]
    asyncio.run(run())
    assert calls==['cancel','finish']
