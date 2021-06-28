import os
from util.database import Databese
from util.alarms import OscAlarm, Alarm
from util.query import get_resultes
from util.email.template import Template
from util.email.send_email import Sender
from dotenv import load_dotenv
import logging
from pathlib import Path
from util.base_function import (
                        check_is_reported,
                        check_is_reported_by_alm_id,
                        log_alarm,
                        validate_osc_in_mut,
                        validate_rem_dupli_wdm,
                        check_is_planedwork
)


# debugFlag = True
debugFlag = False

###############CONFIG########################
BASE_DIR=Path(__file__).resolve().parent
LOG_DIR = (BASE_DIR / "log")
os.makedirs(LOG_DIR, exist_ok=True)
# EMAIL_RECIPIENTS = ["krzysztof.gul@orange.com", "kgul.pl@gmail.com", "GNOCe_BO_TN@orange.com", "GNOCe_FO_TN@orange.com" ]
EMAIL_RECIPIENTS = ["krzysztof.gul@orange.com", "kgul.pl@gmail.com"]
load_dotenv()
db = os.environ.get("DATABASE")
host_db = os.environ.get("HOST_DB")
user_db = os.environ.get("USER_DB")
pass_db = os.environ.get("PASSWORD_DB")
#######################################

logging.basicConfig(format = '%(asctime)s   %(levelname)s:%(message)s', datefmt='%d/%m/%Y %I:%M:%S %p', level=logging.INFO, filename = (LOG_DIR / 'app_osc.log'))

logging.info(f"***Start APP_OSC V2 ***")

if debugFlag:
    EMAIL_RECIPIENTS = ["krzysztof.gul@orange.com", "kgul.pl@gmail.com"]
    from util.query_debug import get_resultes


def debug(x):
    if debugFlag: print(x)

# get results
qr_result_osc_los = get_resultes()
qr_result_mut_los = get_resultes(alarm_query ="MUT_LOS")

# # create obj
if qr_result_osc_los and qr_result_mut_los:
    Databese.initialise(database = db, host = host_db, user = user_db, password = pass_db)
    db_init = True
    osc_alarm_obj = [ OscAlarm(item) for item in qr_result_osc_los]
    mut_alarm_obj = [ Alarm(item) for item in qr_result_mut_los]
else:
    osc_alarm_obj = None
    mut_alarm_obj = None

#validation
if osc_alarm_obj and mut_alarm_obj:
    list_valid_obj = validate_osc_in_mut(osc_alarm_obj, mut_alarm_obj)
    print(f"OSC LOS with MUT LOS alarms nr: {len(list_valid_obj)}")
    logging.info(f"OSC LOS with MUT LOS alarms nr: {len(list_valid_obj)}")
    if list_valid_obj:
        obj_lst_to_render= validate_rem_dupli_wdm(list_valid_obj) 
        debug(f"After removing duplicate sections: {[i for i in obj_lst_to_render]}, count {len(obj_lst_to_render)}")
        logging.info(f"After removing duplicate sections: {len(obj_lst_to_render)}")
        if obj_lst_to_render:
            # check in db if reported base on alarm_id
            obj_lst_to_render = [obj for obj in obj_lst_to_render if not check_is_reported(obj.alarm_id)]  
            print(f"After removing reported alarms by es_alarm_id , stage 1, to the report: {[i for i in obj_lst_to_render]}, count {len(obj_lst_to_render)}")
            logging.info(f"After removing reported alarms by es_alarm_id, to the report: {len(obj_lst_to_render)}")
            
        if obj_lst_to_render:
            # check in db if reported base on alarm_detail
            obj_lst_to_render = [obj for obj in obj_lst_to_render if not check_is_reported_by_alm_id(obj.alarm_detail)]  
            debug(f"After removing reported alarms stage 2 , to the report: {[i for i in obj_lst_to_render]}, count {len(obj_lst_to_render)}")
            logging.info(f"After removing reported alarms(check alarm deatil), to the report: {len(obj_lst_to_render)}")

        if obj_lst_to_render:
             # check in planed work if reported base on section_name
            obj_lst_to_render = list(filter(lambda x: x.section_wdm not in (', ').join(check_is_planedwork()), obj_lst_to_render ))
            debug(f"After removing reported alarms stage 3 , to the report: {[i for i in obj_lst_to_render]}, count {len(obj_lst_to_render)}")
            logging.info(f"After removing reported alarms(check planed work), to the report: {len(obj_lst_to_render)}")
        
    else:
        obj_lst_to_render = None
else:
    obj_lst_to_render = None

if not debugFlag:
    list_msg = []
    if obj_lst_to_render:
        for i in obj_lst_to_render:
            log_alarm(i)
            list_msg.append(i.render())
            logging.info(f"Send: {i.render()}")

    for i in list_msg:
        Sender( subject="TEST OSP: OSC LOS alarm", template_file= "email_osc.txt", template_file_html = "email_osc.html", context = i,  to_emails = EMAIL_RECIPIENTS).send()
        #print(Sender( subject="Test OSC LOS", template_file= "email_osc.txt",  context = i).format_msg())


if debugFlag:
    for i in obj_lst_to_render:
        print("************")
        print(i.alarm_id)
        print(i.port_loca)
        print(i.ne_name)
        print(i.alarm_object)
        print('#')
        print(i.alarm_source_name())
        print(i.set_port_name())
        print(i.get_port_attribute(i.set_port_name()))
        print('#')
        print(i.port_osc_oa())
        print(i.oa_port_name1())
        print(i.oa_port_name2())
        print(i.wdm_section_name())
        print(i.section_wdm)
        print(i.timestamp)


if db_init:
    Databese.close_all_connection()

logging.info(f"***End APP_OSC V2.***")