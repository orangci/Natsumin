from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


@dataclass(slots=True)
class Contract:
	name: str = field()
	passed: bool = field(default=False, repr=True)
	contractor: str = field(default="", repr=False)
	status: str = field(default="", repr=False)
	progress: str = field(default="?/?", repr=False)
	rating: str = field(default="0/10")
	review_url: str = field(default="", repr=False)
	medium: str = field(default="", repr=False)


@dataclass(slots=True)
class User:
	name: str = field()
	status: str = field(default="", repr=False)
	rep: str = field(default="")
	contractor: str = field(default="", repr=False)
	list_url: str = field(default="", repr=False)
	veto_used: bool = field(default=False, repr=False)
	accepting_manhwa: bool = field(default=False, repr=False)
	accepting_ln: bool = field(default=False, repr=False)
	preferences: str = field(default="", repr=False)
	bans: str = field(default="", repr=False)
	contracts: dict[str, Contract] = field(default_factory=dict, repr=False)

	def get_contractor(self, season: "Season") -> Optional["User"]:
		return season.get_user(self.contractor)

	def get_contractee(self, season: "Season") -> Optional["User"]:
		users_with_this_contractor = [user for user in season.users.values() if user.contractor == self.name]
		return users_with_this_contractor[0] if len(users_with_this_contractor) > 0 else None


@dataclass(slots=True)
class SeasonStats:
	users_passed: int = -1
	users: int = -1
	contracts_passed: int = -1
	contracts: int = -1
	contract_types: dict[str, list[int]] = field(default_factory=dict, repr=False)


@dataclass(slots=True)
class Season:
	users: dict[str, User] = field(default_factory=dict, repr=False)
	stats: SeasonStats = None
	reps: dict[str, str] = field(default_factory=dict, repr=False)

	def get_user(self, username: str) -> Optional["User"]:
		return self.users.get(username, None)


# TODO: Start using enums instead of strings where applicable


class ContractType(Enum):
	BASE_CONTRACT = 1
	CHALLENGE_CONTRACT = 2
	BASE_BUDDY = 3
	CHALLENGE_BUDDY = 4
	VETERAN_SPECIAL = 5
	MOVIE_SPECIAL = 6
	VN_SPECIAL = 7
	INDIE_SPECIAL = 8
	EXTREME_SPECIAL = 9


class UserStatusType(Enum):
	PASSED = 1
	FAILED = 2
	LATE_PASS = 3
	INCOMPLETE = 4
