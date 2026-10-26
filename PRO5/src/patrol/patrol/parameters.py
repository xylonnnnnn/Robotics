"""Pure validation shared by startup and runtime parameter updates."""

from dataclasses import dataclass, replace
import math


@dataclass(frozen=True)
class Settings:
    linear_speed: float = 0.5
    turn_rate: float = 0.3
    publish_hz: float = 10.0


LIMITS = {'linear_speed': (0.0, 1.0), 'turn_rate': (-1.0, 1.0),
          'publish_hz': (1.0, 30.0)}


def validate_settings(settings: Settings) -> None:
    for name, (low, high) in LIMITS.items():
        value = getattr(settings, name)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f'{name} must be a finite number')
        if not low <= value <= high:
            raise ValueError(f'{name} must be in [{low}, {high}]')


def updated_settings(current: Settings, changes: dict) -> Settings:
    candidate = replace(current, **{k: v for k, v in changes.items() if k in LIMITS})
    validate_settings(candidate)
    return candidate
