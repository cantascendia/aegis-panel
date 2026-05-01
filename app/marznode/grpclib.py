import asyncio
import atexit
import logging
import ssl
import tempfile

from grpclib import GRPCError
from grpclib.client import Channel
from grpclib.exceptions import StreamTerminatedError

from .base import MarzNodeBase
from .database import MarzNodeDB
from .marznode_grpc import MarzServiceStub
from .marznode_pb2 import (
    UserData,
    UsersData,
    Empty,
    User,
    Inbound,
    BackendConfig,
    BackendLogsRequest,
    Backend,
    RestartBackendRequest,
    BackendStats,
)
from ..models.node import NodeStatus

logger = logging.getLogger(__name__)


def string_to_temp_file(content: str):
    file = tempfile.NamedTemporaryFile(mode="w+t")
    file.write(content)
    file.flush()
    return file


class MarzNodeGRPCLIB(MarzNodeBase, MarzNodeDB):
    def __init__(
        self,
        node_id: int,
        address: str,
        port: int,
        ssl_key: str,
        ssl_cert: str,
        usage_coefficient: int = 1,
    ):
        self.id = node_id
        self._address = address
        self._port = port

        self._key_file = string_to_temp_file(ssl_key)
        self._cert_file = string_to_temp_file(ssl_cert)

        ctx = ssl.create_default_context()
        ctx.load_cert_chain(self._cert_file.name, self._key_file.name)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self._channel = Channel(self._address, self._port, ssl=ctx)
        self._stub = MarzServiceStub(self._channel)
        self._monitor_task = asyncio.create_task(self._monitor_channel())
        self._streaming_task = None

        self._updates_queue = asyncio.Queue(1)
        self.synced = False
        self.usage_coefficient = usage_coefficient
        atexit.register(self._channel.close)

    async def stop(self):
        self._channel.close()
        self._monitor_task.cancel()

    async def _monitor_channel(self):
        # L-032 wave-3 fix (PR will reference upstream marzneshin#TBD if we
        # ever upstream this). Three behavior changes vs the upstream version:
        #
        # 1) `__connect__` timeout 2s → 10s. 2s is too tight for grpclib's
        #    HTTP/2 GOAWAY handling; in production we observed every second
        #    monitor iteration timing out even when marznode was healthy and
        #    the channel was still TLS-connected, because grpclib's
        #    Channel.__connect__() does a full reconnection probe that
        #    involves cert revalidation.
        #
        # 2) Require N consecutive timeouts (default 3) before marking
        #    unhealthy + cancelling streaming task. A single transient
        #    timeout is normal under load; cancelling the SyncUsers stream
        #    on the first timeout was the actual bug — the queue consumer
        #    died and every subsequent panel API user create/delete dropped
        #    silently into _updates_queue with no consumer.
        #
        # 3) Always (re-)spawn streaming task whenever it's missing or done.
        #    Previously it was only spawned in the "first sync after reconnect"
        #    branch; if it ever crashed mid-iteration (e.g. server-side
        #    StreamTerminatedError), it never restarted until full
        #    disconnect-reconnect cycle.
        consecutive_timeouts = 0
        MAX_TIMEOUTS = 3
        CONNECT_TIMEOUT_S = 10
        while state := self._channel._state:
            logger.debug("node %i channel state: %s", self.id, state.value)
            try:
                await asyncio.wait_for(
                    self._channel.__connect__(),
                    timeout=CONNECT_TIMEOUT_S,
                )
            except Exception:
                consecutive_timeouts += 1
                logger.debug(
                    "node %i connect timeout %d/%d",
                    self.id, consecutive_timeouts, MAX_TIMEOUTS,
                )
                if consecutive_timeouts >= MAX_TIMEOUTS:
                    self.set_status(NodeStatus.unhealthy, "timeout")
                    self.synced = False
                    if self._streaming_task:
                        self._streaming_task.cancel()
                        self._streaming_task = None
                    consecutive_timeouts = 0  # reset for retry cycle
            else:
                consecutive_timeouts = 0
                if not self.synced:
                    try:
                        await self._sync()
                    except Exception as e:
                        logger.error(
                            "sync failed for node %i: %s",
                            self.id, e, exc_info=True,
                        )
                        await asyncio.sleep(10)
                        continue
                # Always (re-)spawn streaming task if missing or done.
                # Decoupled from _sync success because SyncUsers stream is
                # independent of RepopulateUsers RPC and should self-heal.
                if (self._streaming_task is None
                        or self._streaming_task.done()):
                    self._streaming_task = asyncio.create_task(
                        self._stream_user_updates()
                    )
                self.set_status(NodeStatus.healthy)
                logger.info("Connected to node %i", self.id)
            await asyncio.sleep(10)

    async def _stream_user_updates(self):
        try:
            async with self._stub.SyncUsers.open() as stream:
                logger.debug("opened the stream")
                while True:
                    user_update = await self._updates_queue.get()
                    logger.debug("got something from queue")
                    user = user_update["user"]
                    await stream.send_message(
                        UserData(
                            user=User(
                                id=user.id,
                                username=user.username,
                                key=user.key,
                            ),
                            inbounds=[
                                Inbound(tag=t) for t in user_update["inbounds"]
                            ],
                        )
                    )
        except (OSError, ConnectionError, GRPCError, StreamTerminatedError):
            logger.info("node %i detached", self.id)
            self.synced = False

    async def update_user(self, user, inbounds: set[str] | None = None):
        if inbounds is None:
            inbounds = set()

        await self._updates_queue.put({"user": user, "inbounds": inbounds})

    async def _repopulate_users(self, users_data: list[dict]) -> None:
        updates = [
            UserData(
                user=User(id=u["id"], username=u["username"], key=u["key"]),
                inbounds=[Inbound(tag=t) for t in u["inbounds"]],
            )
            for u in users_data
        ]
        await self._stub.RepopulateUsers(UsersData(users_data=updates))

    async def fetch_users_stats(self):
        response = await self._stub.FetchUsersStats(Empty())
        return response.users_stats

    async def _fetch_backends(self) -> list:
        response = await self._stub.FetchBackends(Empty())
        return response.backends

    async def _sync(self):
        backends = await self._fetch_backends()
        self.store_backends(backends)
        users = self.list_users()
        await self._repopulate_users(users)
        self.synced = True

    async def get_logs(self, name: str = "xray", include_buffer=True):
        async with self._stub.StreamBackendLogs.open() as stm:
            await stm.send_message(
                BackendLogsRequest(
                    backend_name=name, include_buffer=include_buffer
                )
            )
            while True:
                response = await stm.recv_message()
                yield response.line

    async def restart_backend(
        self, name: str, config: str, config_format: int
    ):
        try:
            await self._stub.RestartBackend(
                RestartBackendRequest(
                    backend_name=name,
                    config=BackendConfig(
                        configuration=config, config_format=config_format
                    ),
                )
            )
            await self._sync()
        except:
            self.synced = False
            self.set_status(NodeStatus.unhealthy)
            raise
        else:
            self.set_status(NodeStatus.healthy)

    async def get_backend_config(self, name: str):
        response: BackendConfig = await self._stub.FetchBackendConfig(
            Backend(name=name)
        )
        return response.configuration, response.config_format

    async def get_backend_stats(self, name: str):
        response: BackendStats = await self._stub.GetBackendStats(
            Backend(name=name)
        )
        return response
