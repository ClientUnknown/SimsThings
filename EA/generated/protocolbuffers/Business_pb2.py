from google.protobuf import descriptor
class ReviewIconData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _REVIEWICONDATA

class ReviewDataUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _REVIEWDATAUPDATE

class BusinessSummaryEntry(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSSUMMARYENTRY

class RestaurantBusinessDataUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _RESTAURANTBUSINESSDATAUPDATE

class RetailBusinessDataUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _RETAILBUSINESSDATAUPDATE

class VetClinicBusinessDataUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _VETCLINICBUSINESSDATAUPDATE

class CustomerBusinessData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _CUSTOMERBUSINESSDATA

class EmployeeBusinessData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class EmployeeData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _EMPLOYEEBUSINESSDATA_EMPLOYEEDATA

    class BusinessUniformData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _EMPLOYEEBUSINESSDATA_BUSINESSUNIFORMDATA

    class BusinessDataPayroll(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

        class BusinessDataPayrollEntry(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
            DESCRIPTOR = _EMPLOYEEBUSINESSDATA_BUSINESSDATAPAYROLL_BUSINESSDATAPAYROLLENTRY

        DESCRIPTOR = _EMPLOYEEBUSINESSDATA_BUSINESSDATAPAYROLL

    DESCRIPTOR = _EMPLOYEEBUSINESSDATA

class SetBusinessData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _SETBUSINESSDATA

class BusinessMarkupUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSMARKUPUPDATE

class BusinessAdvertisementUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSADVERTISEMENTUPDATE

class BusinessDailyCustomersServedUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSDAILYCUSTOMERSSERVEDUPDATE

class BusinessIsOpenUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSISOPENUPDATE

class BusinessFundsUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSFUNDSUPDATE

class BusinessProfitUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSPROFITUPDATE

class BusinessDailyItemsSoldUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSDAILYITEMSSOLDUPDATE

class BusinessDailyCostsUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSDAILYCOSTSUPDATE

class BusinessSummaryDialog(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSSUMMARYDIALOG

class BusinessCustomerUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSCUSTOMERUPDATE

class BusinessCustomerReviewEvent(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSCUSTOMERREVIEWEVENT

class ManageEmployeesDialog(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _MANAGEEMPLOYEESDIALOG

class ManageEmployeeJobData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _MANAGEEMPLOYEEJOBDATA

class ManageEmployeeRowData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _MANAGEEMPLOYEEROWDATA

class BusinessBuffBucketTotal(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSBUFFBUCKETTOTAL

class RestaurantSaveData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _RESTAURANTSAVEDATA

class VetClinicSaveData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _VETCLINICSAVEDATA

class BusinessSaveData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class BusinessFundsCategoryEntry(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _BUSINESSSAVEDATA_BUSINESSFUNDSCATEGORYENTRY

    DESCRIPTOR = _BUSINESSSAVEDATA

class BusinessServiceData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSSERVICEDATA

class AdditionalEmployeeSlotData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _ADDITIONALEMPLOYEESLOTDATA

class BusinessTrackerData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSTRACKERDATA

class BusinessManagerData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _BUSINESSMANAGERDATA

class ManageEmployeeSkillData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _MANAGEEMPLOYEESKILLDATA

class MinEmployeeReqMetUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _MINEMPLOYEEREQMETUPDATE
