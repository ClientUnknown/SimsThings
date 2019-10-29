from protocolbuffers.Localization_pb2 import LocalizedStringTokenfrom sims.sim_info_types import Genderfrom singletons import DEFAULT
class PregnancyOffspringData:

    def __init__(self, age, gender, species, genetics, first_name='', last_name='', traits=DEFAULT):
        self.age = age
        self.gender = gender
        self.species = species
        self.genetics = genetics
        self.first_name = first_name
        self.last_name = last_name
        self.traits = [] if traits is DEFAULT else traits

    @property
    def is_female(self):
        return self.gender == Gender.FEMALE

    def populate_localization_token(self, token):
        token.type = LocalizedStringToken.SIM
        token.first_name = self.first_name
        token.last_name = self.last_name
        token.is_female = self.is_female
