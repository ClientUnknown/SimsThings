from filters.sim_template import TunableSimTemplate, SimTemplateTypefrom sims.occult.occult_enums import OccultTypefrom sims.pregnancy.pregnancy_enums import PregnancyOriginfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableFactory, TunableResourceKey, OptionalTunable, TunablePackSafeReference, TunableReference, Tunable, TunableTuple, TunableList, TunableEnumEntry, TunablePercentfrom sims4.utils import classpropertyfrom singletons import UNSETimport servicesimport sims.sim_spawnerimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('PremadeSimTemplate', default_owner='tingyul')
class PremadeSimCreator(TunableFactory):

    @staticmethod
    def factory(*, first_name, last_name, breed_name, resource_key):
        first_name_key = first_name.hash
        last_name_key = last_name.hash if last_name else UNSET
        breed_name_key = breed_name.hash if breed_name is not None else 0
        return sims.sim_spawner.SimCreator(first_name_key=first_name_key, last_name_key=last_name_key, breed_name_key=breed_name_key, resource_key=resource_key)

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(first_name=TunableLocalizedString(description="\n                The Sim's first name.\n                "), last_name=OptionalTunable(description="\n                The Sim's last name.\n                ", tunable=TunableLocalizedString(), enabled_by_default=True, enabled_name='specify_last_name', disabled_name='no_last_name', disabled_value=UNSET), breed_name=OptionalTunable(description="\n                The Sim's breed name.\n                ", tunable=TunableLocalizedString(), enabled_name='specify_breed_name', disabled_name='no_breed_name'), resource_key=TunableResourceKey(description='\n                The SimInfo file to use.\n                ', default=None, resource_types=(sims4.resources.Types.SIMINFO,)), **kwargs)

class PremadeSimTemplate(TunableSimTemplate):
    INSTANCE_TUNABLES = {'_sim_creation_info': PremadeSimCreator(description='\n            Sim creation info for the premade Sim.\n            '), 'clubs': TunableList(description='\n            Clubs this premade Sim is part of.\n            ', tunable=TunableTuple(seed=TunableReference(description='\n                    The club seed for the premade Sim to be in.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.CLUB_SEED)), leader=Tunable(description='\n                    If enabled, this Sim will be the leader of the club.\n                    ', tunable_type=bool, default=False))), 'career_level': OptionalTunable(description='\n            If specified, the premade Sim will be in the career at this career\n            level.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CAREER_LEVEL))), 'pregnancy': OptionalTunable(description='\n            Whether or not the sim will be pregnant.\n            ', tunable=TunableTuple(other_parent=TunableReference(description='\n                    The other sim whose traits will be passed on to the offspring.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE), class_restrictions='PremadeSimTemplate'), origin=TunableEnumEntry(description='\n                    Define the origin of this pregnancy. This value is used to determine\n                    some of the random elements at birth.\n                    ', tunable_type=PregnancyOrigin, default=PregnancyOrigin.DEFAULT), progress=TunablePercent(description='\n                    Progress into the pregnancy, where 0% is recently conceived\n                    to 100% where labor can happen at any second.\n                    ', default=25))), 'occult': OptionalTunable(description='\n            Whether or not the Sim will have an occult.\n            ', tunable=TunableTuple(occult_type=TunableEnumEntry(description='\n                    The occult type this sim info represents. You do not need to tune\n                    the occult traits on the Sim Template. The traits will be added as\n                    a result of this tuning being set.\n                    ', tunable_type=OccultType, default=OccultType.HUMAN, invalid_enums=(OccultType.HUMAN,)), occult_sim_info=TunableResourceKey(description='\n                    The SimInfo file to use for the occult form of this Sim. It\n                    is assumed that the sim info provided with the Sim Creation\n                    Info is the base/non-occult form.\n                    ', default=None, resource_types=(sims4.resources.Types.SIMINFO,)))), 'primary_aspiration': OptionalTunable(description='\n            Specify the Sims primary aspiration.\n            ', tunable=TunablePackSafeReference(description='\n                The track to give the sim.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK)))}
    household_template = None

    @classproperty
    def template_type(cls):
        return SimTemplateType.PREMADE_SIM

    @classmethod
    def _get_sim_info_creation_data(cls):
        return cls._get_sim_info_resource_data(cls._sim_creation_info.resource_key)

    @classmethod
    def add_template_data_to_sim(cls, sim_info, sim_creator=None):
        super().add_template_data_to_sim(sim_info, sim_creator=sim_creator)
        sim_info.premade_sim_template_id = cls.guid64
