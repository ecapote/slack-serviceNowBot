#!/usr/bin/python36
# Create JIRA from ITSM
#
# written by: Erick Capote
#
# Try with basic function

from objdict import ObjDict
from bs4 import BeautifulSoup
import sys
import os
from configparser import ConfigParser
import logging
import requests

requests.packages.urllib3.disable_warnings()


def setup_custom_logger(name):
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    LOG_FILENAME = os.path.join(__location__, 'ver2-1_create_jira.log')
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler(LOG_FILENAME, mode='a')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def get_jira_tickets(jira_base_url, jira_user, jira_pass):
    logger.info('Get JIRA tickets from EESC and SE')
    try:
        url = jira_base_url + '/search?jql=project in (EESC)&fields=id,key,customfield_10031,' \
                              'status,issuetype,project,description,summary&maxResults=1000'
        logger.info('get_jira_tickets URL: %s' % url)
        headers = {'Content-Type': 'application/json'}
        api_request = requests.get(url, auth=(jira_user, jira_pass), headers=headers, verify=False)
        response_code = api_request.status_code
        logger.info('get_jira_tickets RESPONSE_CODE %s' % response_code)
        if response_code == 200:
            json_response = api_request.json()
            response_dict = json_response
            return response_dict
        else:
            error_response = api_request.text
            response_dict = {response_code: error_response}
            return response_dict
    except Exception as e:
        print(e)
        response_dict = {"get_jira_tickets ERROR": str(e)}
        logger.debug(response_dict)
        return response_dict


def process_jira_info(response):
    jira_search_dict = {}
    my_jira_issues = response['issues']
    logger.info('START process_jira_info PROCESSING')
    if isinstance(my_jira_issues, list):
        for no_issues in range(len(my_jira_issues)):
            jira_search_dict_info = {}
            if 'customfield_10031' in my_jira_issues[no_issues]['fields'].keys():
                jira_case_no = my_jira_issues[no_issues]['key']
                jira_search_dict_info['self'] = my_jira_issues[no_issues]['self']
                jira_search_dict_info['itsm_case_no'] = my_jira_issues[no_issues]['fields']['customfield_10031']
            else:
                jira_case_no = my_jira_issues[no_issues].get('key')
                jira_search_dict_info['self'] = my_jira_issues[no_issues].get('self')
            jira_search_dict[jira_case_no] = jira_search_dict_info
    logger.info('jira_search_dict: %s' % jira_search_dict)
    logger.info('END process_jira_info PROCESSING')
    return jira_search_dict


def chk_jira_created(case_no_to_search, pjira_dict):
    jira_cases = []
    logger.info('Case to check if created: %s' % case_no_to_search)
    for k, v in pjira_dict.items():
        if 'itsm_case_no' in pjira_dict[k]:
            if pjira_dict[k]['itsm_case_no'] is not None:
                jira_cases.append(pjira_dict[k]['itsm_case_no'].lstrip().rstrip())
    logger.info('jira_cases: %s' % jira_cases)
    if case_no_to_search in jira_cases:
        flag = 'true'
        logger.info(case_no_to_search + ' already logged in JIRA')
        logger.info('We got a case match Flag: %s' % flag)
    else:
        flag = 'false'
        logger.info('No match for: %s' % case_no_to_search)
        logger.info('No match flag: %s' % flag)
    return flag


def create_jira_tickets(pitsm_dict, pjira_dict, jira_user, jira_pass, jira_base_url):
    for k, v in pitsm_dict.items():
        ticket_state = v['state'].encode('utf8')
        if (ticket_state != 'Cancelled') and (ticket_state != 'Closed'):
            case_no_to_search = k
            logger.info('Case To Search? %s' % str(case_no_to_search))
            is_jira_created = chk_jira_created(case_no_to_search, pjira_dict)
            logger.info('is_jira_created: %s' % is_jira_created)
            if 'false' in is_jira_created:
                case_no_to_search = str(k)
                my_subject = (v['short_description'])
                logger.info('subject: %s ' % my_subject)
                title_raw = str(case_no_to_search + ' | ' + my_subject)
                logger.info('title_raw: %s' % title_raw)
                title = title_raw.replace('\"', "")
                cleansed_work_notes = v['description'].replace('\"', " ")
                cleansed_work_notes_2 = cleansed_work_notes.replace("\xc2\xa0", "")
                soup = BeautifulSoup(cleansed_work_notes_2, 'html.parser')
                description = cleansed_work_notes
                logger.info('DESCRIPTION_FIELD: %s' % soup)
                result = make_jira_api_call(title, description, case_no_to_search, jira_user, jira_pass, jira_base_url)
                logger.info('MAKE_JIRA_API: %s' % result.keys())
                return result


def get_open_incidents(base_url, incident_assignment_group_id_1, username, password, incident_assignment_group_id_2,
                       incident_assignment_group_id_3):
    url = base_url + '/api/now/table/incident?sysparm_display_value=true&state=Open&s' \
                     'ysparm_query=assignment_group={0}^ORassignment_group={1}^ORassignment_group={2}' \
        .format(incident_assignment_group_id_1, incident_assignment_group_id_2, incident_assignment_group_id_3)
    logger.info('get_open_incidents URL: %s' % url)
    headers = {'Content-Type': 'application/json'}
    api_request = requests.get(url, auth=(username, password), headers=headers, verify=False)
    response_code = api_request.status_code
    if response_code == 200:
        json_response = api_request.json()
        response_dict = json_response
        return response_dict
    else:
        response_dict = {}
        error_response = api_request.text
        response_dict[response_code] = error_response
        return response_dict


def get_new_incidents(base_url, incident_assignment_group_id_1, username, password, incident_assignment_group_id_2,
                      incident_assignment_group_id_3):
    url = base_url + '/api/now/table/incident?sysparm_display_value=true&state=New&' \
                     'sysparm_query=assignment_group={0}^ORassignment_group={1}^ORassignment_group={2}' \
        .format(incident_assignment_group_id_1, incident_assignment_group_id_2, incident_assignment_group_id_3)
    logger.info('get_new_incidents URL: %s' % url)
    headers = {'Content-Type': 'application/json'}
    api_request = requests.get(url, auth=(username, password), headers=headers, verify=False)
    response_code = api_request.status_code
    if response_code == 200:
        json_response = api_request.json()
        response_dict = json_response
        return response_dict
    else:
        response_dict = {}
        error_response = api_request.text
        response_dict[response_code] = error_response
        return response_dict


def get_open_tasks(base_url, username, password, incident_assignment_group_id_1, incident_assignment_group_id_2,
                   incident_assignment_group_id_3):
    url = base_url + '/api/now/table/sn_customerservice_task?sysparm_display_value=true&state=Open&' \
                     'sysparm_query=assignment_group={0}^ORassignment_group={1}^ORassignment_group={2}' \
        .format(incident_assignment_group_id_1, incident_assignment_group_id_2, incident_assignment_group_id_3)
    logger.info('get_open_tasks URL: %s' % url)
    headers = {'Content-Type': 'application/json'}
    api_request = requests.get(url, auth=(username, password), headers=headers, verify=False)
    response_code = api_request.status_code
    if response_code == 200:
        json_response = api_request.json()
        response_dict = json_response
        return response_dict
    else:
        response_dict = {}
        error_response = api_request.text
        response_dict[response_code] = error_response
        return response_dict


def get_open_ritm(base_url, username, password, incident_assignment_group_id_1, incident_assignment_group_id_2,
                  incident_assignment_group_id_3):
    url = base_url + '/api/now/table/sc_req_item?sysparm_display_value=true&' \
                     'sysparm_query=assignment_group={0}^ORassignment_group={1}^ORassignment_group={2}&state=1' \
        .format(incident_assignment_group_id_1, incident_assignment_group_id_2, incident_assignment_group_id_3)
    logger.info('OPEN RITM URL: %s' % url)
    headers = {'Content-Type': 'application/json'}
    api_request = requests.get(url, auth=(username, password), headers=headers, verify=False)
    response_code = api_request.status_code
    logger.info('GET OPEN RITM Resonse Code: %s' % response_code)
    if response_code == 200:
        json_response = api_request.json()
        response_dict = json_response
        logger.info('GET OPEN RITM response_dict: %s' % response_dict)
        return response_dict
    else:
        response_dict = {}
        error_response = api_request.text
        response_dict[response_code] = error_response
        logger.info('GET OPEN RITM Resonse ERROR: %s' % response_dict)
        return response_dict


def get_open_SCTASKS(base_url, username, password, incident_assignment_group_id_1, incident_assignment_group_id_2,
                   incident_assignment_group_id_3):
    url = base_url + '/api/now/table/sc_task?sysparm_display_value=true&state=1&' \
                     'sysparm_query=assignment_group={0}^ORassignment_group={1}^ORassignment_group={2}' \
        .format(incident_assignment_group_id_1, incident_assignment_group_id_2, incident_assignment_group_id_3)
    logger.info('get_open_INC_tasks URL: %s' % url)
    headers = {'Content-Type': 'application/json'}
    api_request = requests.get(url, auth=(username, password), headers=headers, verify=False)
    response_code = api_request.status_code
    if response_code == 200:
        json_response = api_request.json()
        response_dict = json_response
        return response_dict
    else:
        response_dict = {}
        error_response = api_request.text
        response_dict[response_code] = error_response
        return response_dict


def get_open_INC_tasks(base_url, username, password, incident_assignment_group_id_1, incident_assignment_group_id_2,
                   incident_assignment_group_id_3):
    url = base_url + '/api/now/table/incident_task?sysparm_display_value=true&state=1&' \
                     'sysparm_query=assignment_group={0}^ORassignment_group={1}^ORassignment_group={2}' \
        .format(incident_assignment_group_id_1, incident_assignment_group_id_2, incident_assignment_group_id_3)
    logger.info('get_open_INC_tasks URL: %s' % url)
    headers = {'Content-Type': 'application/json'}
    api_request = requests.get(url, auth=(username, password), headers=headers, verify=False)
    response_code = api_request.status_code
    if response_code == 200:
        json_response = api_request.json()
        response_dict = json_response
        return response_dict
    else:
        response_dict = {}
        error_response = api_request.text
        response_dict[response_code] = error_response
        return response_dict


def process_servicenow_tasks(itsm_tickets):
    data = itsm_tickets
    itsm_dict = {}
    for incident in data.items():
        for no_of_incidents in range(len(incident[1])):
            itsm_dict_info = {}
            itsm_incident_no = incident[1][no_of_incidents]['number']
            itsm_dict_info['opened_at'] = incident[1][no_of_incidents]['opened_at']
            itsm_dict_info['assignment_group'] = incident[1][no_of_incidents]['assignment_group']['display_value']
            itsm_dict_info['state'] = incident[1][no_of_incidents]['state']
            itsm_dict_info['sys_updated_on'] = incident[1][no_of_incidents]['sys_updated_on']
            itsm_dict_info['impact'] = incident[1][no_of_incidents]['impact']
            itsm_dict_info['short_description'] = incident[1][no_of_incidents]['short_description']
            itsm_dict_info['comments'] = (incident[1][no_of_incidents]['work_notes'])[:1000]
            itsm_dict_info['opened_by'] = incident[1][no_of_incidents]['opened_by']['display_value']
            itsm_dict_info['parent'] = incident[1][no_of_incidents]['parent']
            itsm_dict_info['sys_id'] = incident[1][no_of_incidents]['sys_id']
            itsm_dict_info['description'] = incident[1][no_of_incidents]['description']
            itsm_dict_info[
                'task_url_link'] = 'https://servicenow.mcp-services.net/nav_to.do?uri=sn_customerservice_task.do?sys_id={}%26sysparm_view=case'.format(
                incident[1][no_of_incidents]['sys_id'])
            itsm_dict[itsm_incident_no] = itsm_dict_info
    logger.info('process_servicenow_DICT_RESPONSE: %r' % itsm_dict)
    return itsm_dict


def make_jira_api_call(my_subject, description, case_no, jira_user, jira_pass, base_url):
    logger.info('make_jira_api_call case number: ' + case_no)
    response_dict = {}
    url = base_url + '/issue/'
    logger.info('jira_api_url: %s' % url)
    headers = {'Content-Type': 'application/json'}
    my_payload = ObjDict()
    my_payload.fields = ObjDict()
    my_payload.fields.project = ObjDict()
    my_payload.fields.project.id = "10084"
    my_payload.fields.summary = my_subject.strip('"')
    my_payload.fields.description = description
    my_payload.fields.issuetype = ObjDict()
    my_payload.fields.issuetype.name = 'Case Escalation'
    my_payload.fields.customfield_10031 = case_no
    my_payload.fields.customfield_10032 = ObjDict()
    customfield_10032_value = ObjDict()
    customfield_10032_value.value = "New"
    my_payload.fields.customfield_10032 = [customfield_10032_value]
    payload = str(my_payload)
    logger.info("make_jira_api_call PAYLOAD: %s" % payload)
    api_request = requests.post(url, auth=(jira_user, jira_pass), headers=headers, data=payload, verify=False)
    logger.info('jira_api_status_code: %s' % api_request.status_code)
    api_response = api_request.json()
    response_dict[api_request.status_code] = api_response
    logger.info('response_dict: ', response_dict)
    return response_dict


def main():
    # Define INI file and set location
    config_info = ConfigParser()
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    ini_location = os.path.join(__location__, 'config.ini')
    config_info.read(ini_location)

    # Get ServiceNOW account info from config file
    usr = config_info.get("serviceNow_creds", "username").strip()
    pwd = config_info.get("serviceNow_creds", "password").strip()
    base_url = config_info.get("serviceNow_creds", "base_url").strip()
    incident_assignment_group_id_1 = config_info.get("serviceNow_creds", "incident_assignment_group_id_1").strip()
    incident_assignment_group_id_2 = config_info.get("serviceNow_creds", "incident_assignment_group_id_2").strip()
    incident_assignment_group_id_3 = config_info.get("serviceNow_creds", "incident_assignment_group_id_3").strip()

    # GET Jira account info from config File
    jira_user = config_info.get('jira_info', 'jira_user').strip("'")
    jira_pass = config_info.get('jira_info', 'jira_pass').strip("'")
    jira_base_url = config_info.get('jira_info', 'jira_base_url').strip("'")


    logger.info('**************START RUN**********************\n')

    # GET JIRA tickets
    jira_tickets_dict = get_jira_tickets(jira_base_url, jira_user, jira_pass)
    logger.info('jira_tickets_dict', jira_tickets_dict)
    processed_jira_results = process_jira_info(jira_tickets_dict)
    logger.info('processed_jira_results: %s' % processed_jira_results)

    # Get OPEN Tasks
    my__open_tsks = get_open_tasks(base_url, usr, pwd, incident_assignment_group_id_1, incident_assignment_group_id_2,
                                   incident_assignment_group_id_3)
    processed_open_tasks = process_servicenow_tasks(my__open_tsks)
    results = create_jira_tickets(processed_open_tasks, processed_jira_results, jira_user, jira_pass, jira_base_url)
    print('OPEN TASKS: ', results)

    # Get NEW INC
    my_new_incidents = get_new_incidents(base_url, incident_assignment_group_id_1, usr, pwd,
                                         incident_assignment_group_id_2, incident_assignment_group_id_3)
    processed_new_incidents = process_servicenow_tasks(my_new_incidents)
    results = create_jira_tickets(processed_new_incidents, processed_jira_results, jira_user, jira_pass, jira_base_url)
    print('New INC: ', results)

    # Get OPEN INC
    my_open_incidents = get_open_incidents(base_url, incident_assignment_group_id_1, usr, pwd,
                                           incident_assignment_group_id_2, incident_assignment_group_id_3)
    processed_open_incidents = process_servicenow_tasks(my_open_incidents)
    results = create_jira_tickets(processed_open_incidents, processed_jira_results, jira_user, jira_pass, jira_base_url)
    print('OPEN INC RESULTS: ', results)

    # Get OPEN RITM
    my_open_ritm = get_open_ritm(base_url, usr, pwd, incident_assignment_group_id_1, incident_assignment_group_id_2,
                                 incident_assignment_group_id_3)
    processed_open_ritm = process_servicenow_tasks(my_open_ritm)
    results = create_jira_tickets(processed_open_ritm, processed_jira_results, jira_user, jira_pass, jira_base_url)
    print('RITM: ', results)

    # Get OPEN INC TASKS
    my_open_inc_tasks = get_open_INC_tasks(base_url, usr, pwd, incident_assignment_group_id_1, incident_assignment_group_id_2,
                                 incident_assignment_group_id_3)
    processed_open_inc_tasks = process_servicenow_tasks(my_open_inc_tasks)
    results = create_jira_tickets(processed_open_inc_tasks, processed_jira_results, jira_user, jira_pass, jira_base_url)
    print('OPEN INC TASKS: ', results)

    # Get OPEN SCTASKS
    my_open_sctasks = get_open_SCTASKS(base_url, usr, pwd, incident_assignment_group_id_1,
                                           incident_assignment_group_id_2,
                                           incident_assignment_group_id_3)
    processed_open_sctasks = process_servicenow_tasks(my_open_sctasks)
    results = create_jira_tickets(processed_open_sctasks, processed_jira_results, jira_user, jira_pass, jira_base_url)
    print('OPEN SCTASKS: ', results)


    logger.info('************** END RUN *************************\n')


if __name__ == '__main__':
    # Instantiate logger
    logger = setup_custom_logger('jira_itsm_ver_21')
    main()
