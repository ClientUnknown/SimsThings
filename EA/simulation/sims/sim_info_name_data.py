from protocolbuffers import SimObjectAttributes_pb2from protocolbuffers.Localization_pb2 import LocalizedStringTokenfrom sims.sim_info_types import Genderimport profanity
class SimInfoNameData:

    def __init__(self, gender, first_name='', last_name='', full_name_key=0):
        self.first_name = first_name
        self.last_name = last_name
        self.gender = gender
        self.full_name_key = full_name_key

    @property
    def is_female(self):
        return self.gender == Gender.FEMALE

    @property
    def always_passes_existence_test(self):
        return True

    def populate_localization_token(self, token):
        token.type = LocalizedStringToken.SIM
        token.first_name = self.first_name
        token.last_name = self.last_name
        token.is_female = self.is_female
        token.full_name_key = self.full_name_key

    @staticmethod
    def generate_sim_info_name_data_msg(sim_info, use_profanity_filter=False):
        sim_info_name_data_msg = SimObjectAttributes_pb2.SimInfoNameData()
        if use_profanity_filter:
            (_, first_name) = profanity.check(sim_info.first_name)
            (_, last_name) = profanity.check(sim_info.last_name)
        else:
            first_name = sim_info.first_name
            last_name = sim_info.last_name
        sim_info_name_data_msg.first_name = first_name
        sim_info_name_data_msg.last_name = last_name
        sim_info_name_data_msg.gender = sim_info.gender
        sim_info_name_data_msg.full_name_key = sim_info.full_name_key
        return sim_info_name_data_msg
