"""Helpers that help with state related things."""
import asyncio
from collections import defaultdict
import logging
from types import ModuleType
from typing import Any, Dict, Iterable, List, Optional, Union

from homeassistant.components.sun import STATE_ABOVE_HORIZON, STATE_BELOW_HORIZON
from homeassistant.const import (
    STATE_CLOSED,
    STATE_HOME,
    STATE_LOCKED,
    STATE_NOT_HOME,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNKNOWN,
    STATE_UNLOCKED,
)
from homeassistant.core import Context, State
from homeassistant.loader import IntegrationNotFound, async_get_integration, bind_hass

from .typing import HomeAssistantType

_LOGGER = logging.getLogger(__name__)


@bind_hass
async def async_reproduce_state(
    hass: HomeAssistantType,
    states: Union[State, Iterable[State]],
    *,
    context: Optional[Context] = None,
    reproduce_options: Optional[Dict[str, Any]] = None,
) -> None:
    """Reproduce a list of states on multiple domains."""
    if isinstance(states, State):
        states = [states]

    to_call: Dict[str, List[State]] = defaultdict(list)

    for state in states:
        to_call[state.domain].append(state)

    async def worker(domain: str, states_by_domain: List[State]) -> None:
        try:
            integration = await async_get_integration(hass, domain)
        except IntegrationNotFound:
            _LOGGER.warning(
                "Trying to reproduce state for unknown integration: %s", domain
            )
            return

        try:
            platform: Optional[ModuleType] = integration.get_platform("reproduce_state")
        except ImportError:
            _LOGGER.warning("Integration %s does not support reproduce state", domain)
            return

        await platform.async_reproduce_states(  # type: ignore
            hass, states_by_domain, context=context, reproduce_options=reproduce_options
        )

    if to_call:
        # run all domains in parallel
        await asyncio.gather(
            *(worker(domain, data) for domain, data in to_call.items())
        )


def state_as_number(state: State) -> float:
    """
    Try to coerce our state to a number.

    Raises ValueError if this is not possible.
    """
    if state.state in (
        STATE_ON,
        STATE_LOCKED,
        STATE_ABOVE_HORIZON,
        STATE_OPEN,
        STATE_HOME,
    ):
        return 1
    if state.state in (
        STATE_OFF,
        STATE_UNLOCKED,
        STATE_UNKNOWN,
        STATE_BELOW_HORIZON,
        STATE_CLOSED,
        STATE_NOT_HOME,
    ):
        return 0

    return float(state.state)
