"""Profile manager for multiple Indy ledger support."""

import logging

from collections import OrderedDict

from ...askar.profile import AskarProfile
from ...config.provider import BaseProvider
from ...config.settings import BaseSettings
from ...config.injector import BaseInjector, InjectionError
from ...cache.base import BaseCache
from ...indy.sdk.profile import IndySdkProfile
from ...ledger.base import BaseLedger
from ...utils.classloader import ClassLoader, ClassNotFoundError

from ..indy import IndySdkLedgerPool, IndySdkLedger
from ..indy_vdr import IndyVdrLedgerPool, IndyVdrLedger

from .base_manager import MultipleLedgerManagerError

LOGGER = logging.getLogger(__name__)


class MultiIndyLedgerManagerProvider(BaseProvider):
    """Multiple Indy ledger support manager provider."""

    askar_manager_path = (
        "aries_cloudagent.ledger.multiple_ledger."
        "indy_vdr_manager.MultiIndyVDRLedgerManager"
    )
    basic_manager_path = (
        "aries_cloudagent.ledger.multiple_ledger." "indy_manager.MultiIndyLedgerManager"
    )
    MANAGER_TYPES = {
        "basic": basic_manager_path,
        "askar-profile": askar_manager_path,
    }

    def __init__(self, root_profile):
        """Initialize the multiple Indy ledger profile manager provider."""
        self._inst = {}
        self.root_profile = root_profile

    def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create the multiple Indy ledger manager instance."""

        if isinstance(self.root_profile, IndySdkProfile):
            manager_type = "basic"
        elif isinstance(self.root_profile, AskarProfile):
            manager_type = "askar-profile"
        else:
            raise MultipleLedgerManagerError(
                "MultiIndyLedgerManagerProvider expects an IndySDKProfile [indy] "
                " or AskarProfile [indy_vdr] as root_profile"
            )

        manager_class = self.MANAGER_TYPES.get(manager_type)

        if manager_class not in self._inst:
            LOGGER.info("Create multiple Indy ledger manager: %s", manager_type)
            try:
                if manager_type == "basic":
                    indy_sdk_production_ledgers = OrderedDict()
                    indy_sdk_non_production_ledgers = OrderedDict()
                    ledger_config_list = settings.get_value("ledger.ledger_config_list")
                    write_ledger_info = None
                    for config in ledger_config_list:
                        keepalive = config.get("keepalive")
                        read_only = config.get("read_only")
                        socks_proxy = config.get("socks_proxy")
                        genesis_transactions = config.get("genesis_transactions")
                        cache = injector.inject_or(BaseCache)
                        ledger_id = config.get("id")
                        pool_name = config.get("pool_name")
                        ledger_is_production = config.get("is_production")
                        ledger_is_write = config.get("is_write")
                        ledger_pool = IndySdkLedgerPool(
                            pool_name,
                            keepalive=keepalive,
                            cache=cache,
                            genesis_transactions=genesis_transactions,
                            read_only=read_only,
                            socks_proxy=socks_proxy,
                        )
                        ledger_instance = IndySdkLedger(
                            pool=ledger_pool,
                            profile=self.root_profile,
                        )
                        if ledger_is_write:
                            write_ledger_info = (ledger_id, ledger_instance)
                        if ledger_is_production:
                            indy_sdk_production_ledgers[ledger_id] = ledger_instance
                        else:
                            indy_sdk_non_production_ledgers[ledger_id] = ledger_instance
                    if settings.get_value("ledger.genesis_transactions"):
                        ledger_instance = self.root_profile.inject_or(BaseLedger)
                        ledger_id = "startup::" + ledger_instance.pool.name
                        indy_sdk_production_ledgers[ledger_id] = ledger_instance
                        if not write_ledger_info:
                            write_ledger_info = (ledger_id, ledger_instance)
                            indy_sdk_production_ledgers.move_to_end(
                                ledger_id, last=False
                            )
                    self._inst[manager_class] = ClassLoader.load_class(manager_class)(
                        self.root_profile,
                        production_ledgers=indy_sdk_production_ledgers,
                        non_production_ledgers=indy_sdk_non_production_ledgers,
                        write_ledger_info=write_ledger_info,
                    )
                else:
                    indy_vdr_production_ledgers = OrderedDict()
                    indy_vdr_non_production_ledgers = OrderedDict()
                    ledger_config_list = settings.get_value("ledger.ledger_config_list")
                    write_ledger_info = None
                    for config in ledger_config_list:
                        keepalive = config.get("keepalive")
                        read_only = config.get("read_only")
                        socks_proxy = config.get("socks_proxy")
                        genesis_transactions = config.get("genesis_transactions")
                        cache = injector.inject_or(BaseCache)
                        ledger_id = config.get("id")
                        pool_name = config.get("pool_name")
                        ledger_is_production = config.get("is_production")
                        ledger_is_write = config.get("is_write")
                        ledger_pool = IndyVdrLedgerPool(
                            pool_name,
                            keepalive=keepalive,
                            cache=cache,
                            genesis_transactions=genesis_transactions,
                            read_only=read_only,
                            socks_proxy=socks_proxy,
                        )
                        ledger_instance = IndyVdrLedger(
                            pool=ledger_pool,
                            profile=self.root_profile,
                        )
                        if ledger_is_write:
                            write_ledger_info = (ledger_id, ledger_instance)
                        if ledger_is_production:
                            indy_vdr_production_ledgers[ledger_id] = ledger_instance
                        else:
                            indy_vdr_non_production_ledgers[ledger_id] = ledger_instance
                    if settings.get_value("ledger.genesis_transactions"):
                        ledger_instance = self.root_profile.inject_or(BaseLedger)
                        ledger_id = "startup::" + ledger_instance.pool.name
                        indy_vdr_production_ledgers[ledger_id] = ledger_instance
                        if not write_ledger_info:
                            write_ledger_info = (ledger_id, ledger_instance)
                            indy_vdr_non_production_ledgers.move_to_end(
                                ledger_id, last=False
                            )
                    self._inst[manager_class] = ClassLoader.load_class(manager_class)(
                        self.root_profile,
                        production_ledgers=indy_vdr_production_ledgers,
                        non_production_ledgers=indy_vdr_non_production_ledgers,
                        write_ledger_info=write_ledger_info,
                    )
            except ClassNotFoundError as err:
                raise InjectionError(
                    f"Unknown multiple Indy ledger manager type: {manager_type}"
                ) from err

        return self._inst[manager_class]