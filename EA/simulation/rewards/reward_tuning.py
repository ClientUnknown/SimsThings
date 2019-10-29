from bucks.bucks_enums import BucksTypefrom bucks.bucks_utils import BucksUtilsfrom buffs.tunable import TunableBuffReferencefrom business.business_reward_tuning import TunableRewardAdditionalEmployeeSlot, TunableRewardAdditionalCustomerCount, TunableRewardAdditionalMarkupfrom clubs.club_enums import ClubGatheringVibefrom objects import ALL_HIDDEN_REASONSfrom objects.object_enums import ItemLocationfrom objects.system import create_objectfrom protocolbuffers import Consts_pb2from protocolbuffers.DistributorOps_pb2 import SetWhimBucksfrom rewards.reward_enums import RewardDestination, RewardTypefrom rewards.tunable_reward_base import TunableRewardBasefrom sims4.localization import LocalizationHelperTuningfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableVariant, TunableReference, Tunable, TunableTuple, TunableCasPart, TunableMagazineCollection, TunableLiteralOrRandomValue, TunableEnumEntry, TunableRange, AutoFactoryInit, TunableFactoryfrom sims4.utils import constpropertyimport build_buyimport servicesimport sims4.resourceslogger = sims4.log.Logger('Rewards', default_owner='trevor')
class TunableRewardObject(TunableRewardBase):
    FACTORY_TUNABLES = {'definition': TunableReference(description='\n            Give an object as a reward.\n            ', manager=services.definition_manager())}

    def __init__(self, *args, definition, **kwargs):
        super().__init__(*args, **kwargs)
        self._definition = definition

    @constproperty
    def reward_type():
        return RewardType.OBJECT_DEFINITION

    def _try_create_in_mailbox(self, sim_info):
        if sim_info.household is None:
            logger.error('Trying to add an item [{}] to a mailbox but the provided sim [{}] has no household', self._definition, sim_info, owner='trevor')
            return False
        zone = services.get_zone(sim_info.household.home_zone_id)
        if zone is None:
            logger.error('Trying to add an item [{}] to a mailbox but the provided sim [{}] has no home zone.', self._definition, sim_info, owner='trevor')
            return False
        lot_hidden_inventory = zone.lot.get_hidden_inventory()
        if lot_hidden_inventory is None:
            logger.error("Trying to add an item [{}] to the lot's hidden inventory but the provided sim [{}] has no hidden inventory for their lot.", self._definition, sim_info, owner='trevor')
            return False
        obj = create_object(self._definition)
        if obj is None:
            logger.error('Trying to give an object reward to a Sim, {}, and the object created was None. Definition: {}', sim_info, self._definition)
            return False
        else:
            try:
                lot_hidden_inventory.system_add_object(obj)
            except:
                logger.error('Could not add object [{}] to the mailbox inventory on the home lot of the Sim [{}].', obj, sim_info, owner='trevor')
                obj.destroy(source=self, cause='Could not add object to the mailbox inventory')
                return False
        return True

    def _try_create_in_sim_inventory(self, sim_info, obj=None, force_rewards_to_sim_info_inventory=False):
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            if force_rewards_to_sim_info_inventory:
                obj = create_object(self._definition) if obj is None else obj
                return sim_info.try_add_object_to_inventory_without_component(obj)
            return (False, None)
        obj = create_object(self._definition) if obj is None else obj
        if obj is None:
            logger.error('Trying to give an object reward to a Sim, {}, and the object created was None. Definition: {}', sim_info, self._definition)
            return (False, None)
        result = sim.inventory_component.player_try_add_object(obj)
        if not result:
            return (False, obj)
        obj.update_ownership(sim_info)
        return (True, obj)

    def _try_create_in_household_inventory(self, sim_info, obj=None):
        obj = create_object(self._definition, loc_type=ItemLocation.HOUSEHOLD_INVENTORY) if obj is None else obj
        if obj is None:
            logger.error('Trying to give an object reward to a Sim, {}, and the object created was None. Definition: {}', sim_info, self._definition)
            return (False, None)
        obj.update_ownership(sim_info, make_sim_owner=False)
        obj.set_post_bb_fixup_needed()
        if not build_buy.move_object_to_household_inventory(obj):
            logger.error('Failed to add reward definition object {} to household inventory.', self._definition, owner='rmccord')

    def open_reward(self, sim_info, reward_destination=RewardDestination.HOUSEHOLD, force_rewards_to_sim_info_inventory=False, **kwargs):
        if reward_destination == RewardDestination.MAILBOX:
            self._try_create_in_mailbox(sim_info)
            return
        reward_object = None
        if reward_destination == RewardDestination.SIM:
            (result, reward_object) = self._try_create_in_sim_inventory(sim_info, force_rewards_to_sim_info_inventory=force_rewards_to_sim_info_inventory)
            if result:
                return
        self._try_create_in_household_inventory(sim_info, obj=reward_object)

    def _get_display_text(self, resolver=None):
        return LocalizationHelperTuning.get_object_name(self._definition)

class TunableRewardCASPart(TunableRewardBase):
    FACTORY_TUNABLES = {'cas_part': TunableCasPart(description='\n            The cas part for this reward.\n            ')}

    def __init__(self, *args, cas_part, **kwargs):
        super().__init__(*args, **kwargs)
        self._cas_part = cas_part

    @constproperty
    def reward_type():
        return RewardType.CAS_PART

    def open_reward(self, sim_info, **kwargs):
        household = sim_info.household
        household.add_cas_part_to_reward_inventory(self._cas_part)

    def valid_reward(self, sim_info):
        return not sim_info.household.part_in_reward_inventory(self._cas_part)

class TunableRewardMoney(TunableRewardBase):
    FACTORY_TUNABLES = {'money': TunableLiteralOrRandomValue(description='\n            Give money to a sim/household.\n            ', tunable_type=int, default=10)}

    def __init__(self, *args, money, **kwargs):
        super().__init__(*args, **kwargs)
        self._awarded_money = money.random_int()

    @constproperty
    def reward_type():
        return RewardType.MONEY

    def open_reward(self, sim_info, **kwargs):
        household = services.household_manager().get(sim_info.household_id)
        if household is not None:
            household.funds.add(self._awarded_money, Consts_pb2.TELEMETRY_MONEY_ASPIRATION_REWARD, sim_info.get_sim_instance())

    def _get_display_text(self, resolver=None):
        return LocalizationHelperTuning.get_money(self._awarded_money)

class TunableRewardTrait(TunableRewardBase):
    FACTORY_TUNABLES = {'trait': TunableReference(description='\n            Give a trait as a reward\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT))}

    def __init__(self, *args, trait, **kwargs):
        super().__init__(*args, **kwargs)
        self._trait = trait

    @constproperty
    def reward_type():
        return RewardType.TRAIT

    def open_reward(self, sim_info, reward_destination=RewardDestination.HOUSEHOLD, **kwargs):
        if reward_destination == RewardDestination.HOUSEHOLD:
            household = sim_info.household
            for sim in household.sim_info_gen():
                sim.add_trait(self._trait)
        elif reward_destination == RewardDestination.SIM:
            sim_info.add_trait(self._trait)
        else:
            logger.warn('Attempting to open a RewardTrait with an invalid destination: {}. Reward traits can only be given to households or sims.', reward_destination, owner='trevor')

    def valid_reward(self, sim_info):
        return sim_info.trait_tracker.can_add_trait(self._trait)

class TunableRewardBuildBuyUnlockBase(TunableRewardBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = None
        self.type = Types.INVALID

    def get_resource_key(self):
        return NotImplementedError

    def open_reward(self, sim_info, reward_destination=RewardDestination.HOUSEHOLD, **kwargs):
        key = self.get_resource_key()
        if key is not None:
            if reward_destination == RewardDestination.SIM:
                sim_info.add_build_buy_unlock(key)
            elif reward_destination == RewardDestination.HOUSEHOLD:
                for household_sim_info in sim_info.household.sim_info_gen():
                    household_sim_info.add_build_buy_unlock(key)
            else:
                logger.warn('Invalid reward destination () on build buy unlock. The household will still get the buildbuy unlock added.', reward_destination, owner='trevor')
            sim_info.household.add_build_buy_unlock(key)
        else:
            logger.warn('Invalid Build Buy unlock tuned. No reward given.')

class TunableBuildBuyObjectDefinitionUnlock(TunableRewardBuildBuyUnlockBase):

    @TunableFactory.factory_option
    def get_definition(pack_safe):
        return {'object_definition': TunableReference(description='\n                The definition of the object to be created.\n                ', manager=services.definition_manager(), pack_safe=pack_safe)}

    def __init__(self, *args, object_definition, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = object_definition
        self.type = Types.OBJCATALOG

    @constproperty
    def reward_type():
        return RewardType.BUILD_BUY_OBJECT

    def get_resource_key(self):
        return sims4.resources.Key(self.type, self.instance.id)

class TunableBuildBuyMagazineCollectionUnlock(TunableRewardBuildBuyUnlockBase):
    FACTORY_TUNABLES = {'magazine_collection': TunableMagazineCollection(description='\n            Unlock a magazine room to purchase in build/buy.\n            ')}

    def __init__(self, *args, magazine_collection, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = magazine_collection
        self.type = Types.MAGAZINECOLLECTION

    @constproperty
    def reward_type():
        return RewardType.BUILD_BUY_MAGAZINE_COLLECTION

    def get_resource_key(self):
        if self.instance is not None:
            return sims4.resources.Key(self.type, self.instance)
        else:
            return

class TunableSetClubGatheringVibe(TunableRewardBase):
    FACTORY_TUNABLES = {'vibe_to_set': TunableEnumEntry(description='\n            The vibe that the club gathering will be set to.\n            ', tunable_type=ClubGatheringVibe, default=ClubGatheringVibe.NO_VIBE)}

    def __init__(self, *args, vibe_to_set=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._vibe_to_set = vibe_to_set

    @constproperty
    def reward_type():
        return RewardType.SET_CLUB_GATHERING_VIBE

    def get_resource_key(self):
        return NotImplementedError

    def open_reward(self, sim_info, **kwargs):
        club_service = services.get_club_service()
        if club_service is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is None:
            return
        gathering = club_service.sims_to_gatherings_map.get(sim, None)
        if gathering is None:
            return
        gathering.set_club_vibe(self._vibe_to_set)

class TunableRewardDisplayText(TunableRewardBase):

    @constproperty
    def reward_type():
        return RewardType.DISPLAY_TEXT

    def open_reward(self, _, **kwargs):
        return True

class TunableRewardBucks(AutoFactoryInit, TunableRewardBase):
    FACTORY_TUNABLES = {'bucks_type': TunableEnumEntry(description='\n            The type of Bucks to grant.\n            ', tunable_type=BucksType, default=BucksType.INVALID, invalid_enums=(BucksType.INVALID,)), 'amount': TunableRange(description='\n            The amount of Bucks to award. Must be a positive value.\n            ', tunable_type=int, default=10, minimum=1)}

    @constproperty
    def reward_type():
        return RewardType.BUCKS

    def open_reward(self, sim_info, **kwargs):
        if sim_info.is_npc:
            return
        tracker = BucksUtils.get_tracker_for_bucks_type(self.bucks_type, sim_info.id, add_if_none=True)
        if tracker is None:
            logger.error('Failed to open a TunableRewardBucks of buck type {} for Sim {}.', self.bucks_type, sim_info)
            return
        tracker.try_modify_bucks(self.bucks_type, self.amount)

class TunableRewardBuff(AutoFactoryInit, TunableRewardBase):
    FACTORY_TUNABLES = {'buff': TunableBuffReference(description='\n            Buff to be given as a reward.\n            ')}

    @constproperty
    def reward_type():
        return RewardType.BUFF

    def open_reward(self, sim_info, reward_destination=RewardDestination.HOUSEHOLD, **kwargs):
        if reward_destination == RewardDestination.HOUSEHOLD:
            household = sim_info.household
            for sim_info in household.sim_info_gen():
                sim_info.add_buff_from_op(buff_type=self.buff.buff_type, buff_reason=self.buff.buff_reason)
        elif reward_destination == RewardDestination.SIM:
            sim_info.add_buff_from_op(buff_type=self.buff.buff_type, buff_reason=self.buff.buff_reason)
        else:
            logger.error('Attempting to open a RewardBuff with an invalid destination: {}. Reward buffs can only be given to households or Sims.', reward_destination)

class TunableRewardWhimBucks(AutoFactoryInit, TunableRewardBase):
    FACTORY_TUNABLES = {'whim_bucks': TunableRange(description='\n            The number of whim bucks to give.\n            ', tunable_type=int, default=1, minimum=1)}

    @constproperty
    def reward_type():
        return RewardType.WHIM_BUCKS

    def open_reward(self, sim_info, reward_destination=RewardDestination.HOUSEHOLD, **kwargs):
        if reward_destination == RewardDestination.HOUSEHOLD:
            household = sim_info.household
            for sim_info in household.sim_info_gen():
                sim_info.add_whim_bucks(self.whim_bucks, SetWhimBucks.COMMAND)
        elif reward_destination == RewardDestination.SIM:
            sim_info.add_whim_bucks(self.whim_bucks, SetWhimBucks.COMMAND)
        else:
            logger.error('Attempting to open a RewardWhimBucks with an invalid destination: {}. Reward whim bucks can only be given to households or Sims.', reward_destination)

class TunableSpecificReward(TunableVariant):

    def __init__(self, description='A single specific reward.', pack_safe=False, **kwargs):
        super().__init__(money=TunableRewardMoney.TunableFactory(), object_definition=TunableRewardObject.TunableFactory(), trait=TunableRewardTrait.TunableFactory(), cas_part=TunableRewardCASPart.TunableFactory(), build_buy_object=TunableBuildBuyObjectDefinitionUnlock.TunableFactory(get_definition=(pack_safe,)), build_buy_magazine_collection=TunableBuildBuyMagazineCollectionUnlock.TunableFactory(), display_text=TunableRewardDisplayText.TunableFactory(), additional_employee_slot=TunableRewardAdditionalEmployeeSlot.TunableFactory(), additional_business_customer_count=TunableRewardAdditionalCustomerCount.TunableFactory(), additional_business_markup=TunableRewardAdditionalMarkup.TunableFactory(), set_club_gathering_vibe=TunableSetClubGatheringVibe.TunableFactory(), bucks=TunableRewardBucks.TunableFactory(), buff=TunableRewardBuff.TunableFactory(), whim_bucks=TunableRewardWhimBucks.TunableFactory(), description=description, **kwargs)

class TunableRandomReward(TunableTuple):

    def __init__(self, description='A list of specific rewards and a weight.', **kwargs):
        super().__init__(reward=TunableSpecificReward(), weight=Tunable(tunable_type=float, default=1), description=description)
