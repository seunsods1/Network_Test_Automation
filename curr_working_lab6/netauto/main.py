#!/usr/bin/env python3
from ansible_playbook_runner import Runner
from jinja2 import Environment, FileSystemLoader
from io import StringIO
from flask import Flask, render_template, request, session, send_file, send_from_directory
import re
import sys
import webbrowser
import os, os.path
from os import path
import ast, shutil
import time, json
import endpoint_pbrun, idealop_pbrun, optest_junos_funcs, optest_cisco_funcs, optest_arista_funcs
import yaml, wget, subprocess
from threading import Thread
from multiprocessing import Process
from collections import OrderedDict
from pathlib import Path
import subprocess, docker

################dictionary constructor for optical commands and their results pulled from optic
op_dict, op_cmds_lst, op_lst = {}, [], []
def optical_dict_const(op_dict, op_cmds_lst, op_lst):
    for opresult in op_lst:
        for cmd in op_cmds_lst:
            if opresult['command'] == cmd:
                op_dict[cmd] = opresult['stdout_lines']
    return op_dict

def idealoptic(ideal_op_id, jun_idprom_cmd):
    idealop_pbrun.idealop_playb(ideal_op_id, jun_idprom_cmd)
    pass

def tb_intpull():
    #########################################################################################
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    tb_path = auth_dict['TB']['ansi_path']
    sw_func, sw_vendor, username, passwd = auth_dict['TB']['sw_func'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass']
    #########################################################################################
    env = Environment(loader=FileSystemLoader('.'))
    templ = env.get_template(tb_path + "/int_pull_playb.j2")
    with open(tb_path + "/int_pull_playb.yml", "w") as fl:
        fl.write(templ.render(sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))
    ############Run playbook to Gather Interface data to determine ports with optics#####################
    pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/int_pull_playb.yml')
    res = pbrun.run()
    pass

def dom_pull_pbrun():
    tsart_dom_pull = time.time()
    #################################################################################
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    tb_path = auth_dict['TB']['ansi_path']
    sw_func, sw_vendor, username, passwd = auth_dict['TB']['sw_func'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass']
    #################################################################################
    if sw_vendor == 'juniper':
        with open("temp_power_chk_pb_path",'r') as fl:
            power_chk_pb_path = fl.read()
        playbrun = Runner([tb_path + '/inventory/inven.ini'], power_chk_pb_path)
        result = playbrun.run()
    if sw_vendor == 'cisco':
        with open('int_pull.json') as fl:
            int_pull = ast.literal_eval(fl.read().strip())
            int_pull = [re.sub(' +',' ',i) for i in int_pull]
            int_lst = []
            for line in int_pull:
                if 'connected' == line.split(' ')[1]:
                    int_lst.append(line)
            interface_lst = [val.split(' ')[0] for val in int_lst]
        port_id_dict = {}
        for id in interface_lst:
            port_id_dict[id] = id.replace('/','_')

        env = Environment(loader=FileSystemLoader('.'))
        templ = env.get_template(tb_path + "/op_power_chk_playb.j2")
        templ2 = env.get_template(tb_path + "/templates/op_power_chk_temp.j2")
        with open('/netauto/ansiblefiles/cisco_ios_ansiblefil/templates/op_power_chk.j2','w') as fl:
            fl.write(templ2.render(port_id_dict=port_id_dict))
        with open(tb_path + "/op_power_chk_playb.yml", "w") as fl:
            fl.write(templ.render(sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd, port_id_dict=port_id_dict))
        pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/op_power_chk_playb.yml')
        res = pbrun.run()

    if sw_vendor == 'arista':
        with open('int_pull.json') as fl:
            int_pull = ast.literal_eval(fl.read().strip())
            int_pull = [re.sub(' +',' ',i) for i in int_pull]
            int_lst = []
            for line in int_pull:
                if 'connected' == line.split(' ')[1]:
                    int_lst.append(line)
            interface_lst = [val.split(' ')[0] for val in int_lst]

        env = Environment(loader=FileSystemLoader('.'))
        templ = env.get_template(tb_path + "/op_power_chk_playb.j2")
        templ2 = env.get_template(tb_path + "/templates/op_power_chk_temp.j2")
        with open('/netauto/ansiblefiles/arista_eos_ansiblefil/templates/op_power_chk.j2','w') as fl:
            fl.write(templ2.render(interface_lst=interface_lst))
        with open(tb_path + "/op_power_chk_playb.yml", "w") as fl:
            fl.write(templ.render(sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd, interface_lst=interface_lst))
        pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/op_power_chk_playb.yml')
        res = pbrun.run()

    tend_dom_pull = time.time()
    print('dom_pull_pbrun Duration: {:.4f}'.format(tend_dom_pull - tsart_dom_pull))
    pass

def optical_power_pull_endp():
    tsart_op_power_endp = time.time()

    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    tb_path = auth_dict['TB']['ansi_path']
    sw_func, sw_vendor, username, passwd = auth_dict['TB']['sw_func'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass']

    if sw_vendor == 'juniper':
        with open("interface_lst_tmp.txt",'r') as fl:
            interface_lst = ast.literal_eval(fl.read())
        endpoint_dict = OrderedDict()
        print("This is int_List: ",interface_lst, " Type: ",type(interface_lst))
        for port_id in interface_lst:
            endpoint_data = endpoint_pbrun.endpoint_pbrun(port_id)
            endpoint_dict[port_id] = endpoint_data
        with open("endpoint_data_tmp.json", "w") as fl:
            json.dump(endpoint_dict, fl)

    if sw_vendor == 'cisco':
        with open('int_pull.json') as fl:
            int_pull = ast.literal_eval(fl.read().strip())
            int_pull = [re.sub(' +',' ',i) for i in int_pull]
            int_lst = []
            for line in int_pull:
                if 'connected' == line.split(' ')[1]:
                    int_lst.append(line)
            interface_lst = [val.split(' ')[0] for val in int_lst]
            endpoint_dict = OrderedDict()
            for port_id in interface_lst:
                endpoint_data = endpoint_pbrun.endpoint_pbrun(port_id)
                endpoint_dict[port_id] = endpoint_data
            with open("endpoint_data_tmp.json", "w") as fl:
                json.dump(endpoint_dict, fl)

    if sw_vendor == 'arista':
        with open('int_pull.json') as fl:
            int_pull = ast.literal_eval(fl.read().strip())
            int_pull = [re.sub(' +',' ',i) for i in int_pull]
            int_lst = []
            for line in int_pull:
                if 'connected' == line.split(' ')[1]:
                    int_lst.append(line)
            interface_lst = [val.split(' ')[0] for val in int_lst]
            endpoint_dict = OrderedDict()
            for port_id in interface_lst:
                endpoint_data = endpoint_pbrun.endpoint_pbrun(port_id)
                endpoint_dict[port_id] = endpoint_data
            with open("endpoint_data_tmp.json", "w") as fl:
                json.dump(endpoint_dict, fl)

    tend_op_power_endp = time.time()

    print('optical_power_pull_endp Duration: {:.4f}'.format(tend_op_power_endp - tsart_op_power_endp))
    pass


def optical_data_analysis(port_id, domlst_per_id, optest_per_sn, user_dict):
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    tb_path = auth_dict['TB']['ansi_path']
    sw_func, sw_vendor, username, passwd = auth_dict['TB']['sw_func'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass']    ################open dictionary containing serial numbers of optic at part id###########################

    if sw_vendor == 'cisco':
        dom_res = optest_cisco_funcs.cisco_optical_power_eval(domlst_per_id, sw_func, sw_vendor, username, passwd)
        ##Store individual optical results dicts in master optest_dict
        optest_dict = OrderedDict()
        optest_dict['port_id'] = port_id
        optest_dict.update(dom_res)
        ###################Comparing TX and RX pulled from Endpoint Optics to the TX and RX pulled from Testbed Optics
        testbed_op_tx = optest_dict["txval"]
        testbed_op_rx = optest_dict["rxval"]
        ###Store dictionary containing user input "user_dict" in optest_dict
        optest_dict.update(user_dict)

    if sw_vendor == 'arista':
        dom_res = optest_arista_funcs.arista_optical_power_eval(domlst_per_id)
        ##Store individual optical results dicts in master optest_dict
        optest_dict = OrderedDict()
        optest_dict['port_id'] = port_id
        optest_dict.update(dom_res)
        ###################Comparing TX and RX pulled from Endpoint Optics to the TX and RX pulled from Testbed Optics
        testbed_op_tx = optest_dict["txval"]
        testbed_op_rx = optest_dict["rxval"]
        ###Store dictionary containing user input "user_dict" in optest_dict
        optest_dict.update(user_dict)


    if sw_vendor == 'juniper':
        with open('tmp_sn_dict.json') as fl:
            tmp_sn_dict = json.load(fl)

        print('this is dom_pull_per_id in thread: ',domlst_per_id)
        dom_res = optest_junos_funcs.dom_parse(domlst_per_id, tmp_sn_dict[port_id[7:]])

        ##Store individual optical results dicts in master optest_dict
        optest_dict = OrderedDict()
        optest_dict['port_id'] = port_id
        optest_dict.update(dom_res)
        #########################################BEGINNING of changes########################################################################
        optest_dict.update(optest_junos_funcs.opdata_eval(optest_dict))
        ###Store dictionary containing user input "user_dict" in optest_dict
        optest_dict.update(user_dict)

        ###################Comparing TX and RX pulled from Endpoint Optics to the TX and RX pulled from Testbed Optics
        testbed_op_tx = float(re.findall(r'[-+]?\d*\.?\d+|\d+', optest_dict["txval"])[1])
        testbed_op_rx = float(re.findall(r'[-+]?\d*\.?\d+|\d+', optest_dict["rxval"])[1])


    ###########Optical budget check; comparing TX and RX powers of testbed optics with endpoint optics###################################
    ################extracting endpoint1 and 2's TX and RX power from function endpoint_pbrun() of module endpoint_pbrun#############
    with open("endpoint_data_tmp.json") as fl:
        endpoint_dict = json.load(fl)

    endpoint_tx = endpoint_dict[port_id]['endpoint_tx']
    endpoint_rx = endpoint_dict[port_id]['endpoint_rx']


    print('This is TX and RX power', testbed_op_tx, testbed_op_rx, type(testbed_op_tx), type(testbed_op_rx))
    print('This is TX and RX power endp', endpoint_tx, endpoint_rx, type(endpoint_tx), type(endpoint_rx))

    try:
        atten = int(optest_dict['atten'])
    except:
        atten = 0

############################Determining if power budget for Transmit port of testbed optic is met###############################
    if (((endpoint_rx >= round(((testbed_op_tx - atten)-3),2)))  and (endpoint_rx <= round(((testbed_op_tx - atten)+3),2))):
        optest_dict['powerbudget_pass_tx'] = True
        print('This is TX and RX power', testbed_op_tx, testbed_op_rx, type(testbed_op_tx), type(testbed_op_rx))
        print('This is TX and RX power endp', endpoint_tx, endpoint_rx, type(endpoint_tx), type(endpoint_rx))
        print('This is atten', atten, type(atten))
        optest_dict['powerbudget_dev_tx'] = round(endpoint_rx-(testbed_op_tx - atten),2)
#        optest_dict['powerbudget_dev_tx_percent'] = str(round(((optest_dict['powerbudget_dev_tx']/(testbed_op_tx - atten))*100),2)) + ' %'

    else:
        optest_dict['powerbudget_pass_tx'] = False
        optest_dict['powerbudget_dev_tx'] = round(endpoint_rx-(testbed_op_tx - atten),2)
    #    optest_dict['powerbudget_dev_tx_percent'] = str(round(((optest_dict['powerbudget_dev_tx']/(testbed_op_tx - atten))*100),2)) + ' %'

############################Determining if power budget for Receive port of testbed optic is met###############################
    if ((testbed_op_rx >= round(((endpoint_tx - atten)-3),2))  and (testbed_op_rx <= round(((endpoint_tx - atten)+3),2))):
        optest_dict['powerbudget_pass_rx'] = True
        optest_dict['powerbudget_dev_rx'] = round(testbed_op_rx-(endpoint_tx - atten),2)
#        optest_dict['powerbudget_dev_rx_percent'] = str(round(((optest_dict['powerbudget_dev_rx']/(endpoint_tx - atten))*100),2)) + ' %'

    else:
        optest_dict['powerbudget_pass_rx'] = False
        optest_dict['powerbudget_dev_rx'] = round(testbed_op_rx-(endpoint_tx - atten),2)

    optest_per_sn[port_id] = optest_dict




    #    print('optest_per_sn: ',port_id," ", optest_per_sn)
    #    optest_per_sn[port_id] = optest_dict

####################-----> THE BEGINNING ########################################################################################################################
########################Defining flask object ####
app = Flask(__name__)
app.secret_key = 'password'

@app.route('/', methods=["GET", "POST"])
def auth_page():
    return render_template("authentication_page.j2")

########Input##########################
@app.route('/enter_so', methods=["GET", "POST"])
def enter_so():
    #############Pulling authentication data from "authentication_page.j2"#######
    auth_dict = OrderedDict()
    auth_dict['TB'], auth_dict['End1'], auth_dict['End2'] = OrderedDict(), OrderedDict(), OrderedDict()
    auth_dict['TB']['ip'], auth_dict['TB']['usrname'], auth_dict['TB']['pass'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['sw_func'] = request.args.get('tb_ip'), request.args.get('tb_usr'), request.args.get('tb_pass'), request.args.get('tb_sw_vendor'), 'testbed'
    auth_dict['End1']['ip'], auth_dict['End1']['usrname'], auth_dict['End1']['pass'], auth_dict['End1']['sw_vendor'], auth_dict['End1']['sw_func'] = request.args.get('end1_ip'), request.args.get('end1_usr'), request.args.get('end1_pass'), request.args.get('end1_sw_vendor'), 'endpoint1'
    auth_dict['End2']['ip'], auth_dict['End2']['usrname'], auth_dict['End2']['pass'], auth_dict['End2']['sw_vendor'], auth_dict['End2']['sw_func'] = request.args.get('end2_ip'), request.args.get('end2_usr'), request.args.get('end2_pass'), request.args.get('end2_sw_vendor'), 'endpoint2'

    ##############################################################################################################
    tb_sw_vendor, end1_sw_vendor, end2_sw_vendor = request.args.get('tb_sw_vendor'), request.args.get('end1_sw_vendor'), request.args.get('end2_sw_vendor')
    path_ansible_arista, path_ansible_cisco, path_ansible_junos = 'ansiblefiles/arista_eos_ansiblefil', 'ansiblefiles/cisco_ios_ansiblefil', 'ansiblefiles/junos_ansiblefil'

    ################################################################################################################
    ######Build Inventory and Group variable using data gotting from "auth_dict"############
    ###Building Group var for TB########

    #########Store inventory data for each switch vendor in different dictionaries###################
    inven_junos_dict, inven_cisco_dict, inven_arista_dict = OrderedDict(), OrderedDict(), OrderedDict()
    print(auth_dict)

#    sw_ven_ans_dict = OrderedDict()

    for k,v in auth_dict.items():
        sw_ven_ans_dict = {}
        print(k)
        print(v)
        print(v['sw_vendor'])
        if (v['sw_vendor'] == 'juniper'):
            env = Environment(loader=FileSystemLoader('.'))
            templ_inv = env.get_template("./ansiblefiles/junos_ansiblefil/inventory/inven.j2")
            templ_usr_auth = env.get_template("./ansiblefiles/usr_auth/all_auth.j2")
            with open("./ansiblefiles/junos_ansiblefil/inventory/inven.ini", 'a') as fl:
                fl.write(templ_inv.render(sw_func = v['sw_func'], sw_ip = v['ip']))
                fl.write('\n')
                fl.write('\n')
            #sw_func = v['sw_func']
        #    print(sw_func, type(sw_func))
            sw_ven_juni_dict = {}
            #sw_ven_juni_dict['juniper'] = {}


            sw_ven_juni_dict['sw_func'] = v['sw_func']
            sw_ven_juni_dict['sw_vendor'] = 'juniper'
            sw_ven_juni_dict['ansi_path'] = path_ansible_junos
            print(sw_ven_juni_dict)
            """
            with open("./ansiblefiles/junos_ansiblefil/group_vars/all.yml", 'w') as fl:
                fl.write(templ_usr_auth.render(usrname = v['usrname'], passwd = v['pass']))
            """
            ####################################################################################
            v['ansi_path'] = path_ansible_junos

            ####################################################################################

        if (v['sw_vendor'] == 'cisco'):
            env = Environment(loader=FileSystemLoader('.'))
            templ_inv = env.get_template("./ansiblefiles/cisco_ios_ansiblefil/inventory/inven.j2")
            templ_usr_auth = env.get_template("./ansiblefiles/usr_auth/all_auth.j2")
            with open("./ansiblefiles/cisco_ios_ansiblefil/inventory/inven.ini", 'a') as fl:
                fl.write(templ_inv.render(sw_func = v['sw_func'], sw_ip = v['ip']))
                fl.write('\n')
                fl.write('\n')

            sw_ven_cis_dict = {}
        #    sw_ven_cis_dict['cisco'] = {}
        #    sw_func = v['sw_func']
            sw_ven_cis_dict['sw_func'] = v['sw_func']
            sw_ven_cis_dict['sw_vendor'] = 'cisco'
            sw_ven_cis_dict['ansi_path'] = path_ansible_cisco

            print(sw_ven_cis_dict)

            ####################################################################################
            v['ansi_path'] = path_ansible_cisco

            ####################################################################################


        if (v['sw_vendor'] == 'arista'):
            env = Environment(loader=FileSystemLoader('.'))
            templ_inv = env.get_template("./ansiblefiles/arista_eos_ansiblefil/inventory/inven.j2")
            templ_usr_auth = env.get_template("./ansiblefiles/usr_auth/all_auth.j2")
            with open("./ansiblefiles/arista_eos_ansiblefil/inventory/inven.ini", 'a') as fl:
                fl.write(templ_inv.render(sw_func = v['sw_func'], sw_ip = v['ip']))
                fl.write('\n')
                fl.write('\n')

            sw_ven_ari_dict = {}
            sw_ven_ari_dict['arista'] = {}
        #    sw_func = v['sw_func']
            sw_ven_ari_dict['sw_func'] = v['sw_func']
            sw_ven_ari_dict['sw_vendor'] = 'arista'
            sw_ven_ari_dict['ansi_path'] = path_ansible_arista

            print(sw_ven_ari_dict)

            ####################################################################################
            v['ansi_path'] = path_ansible_arista

            ####################################################################################


    """
    print('This is juni', sw_ven_juni_dict)
    print('This is cis', sw_ven_cis_dict)
    print('This is ari', sw_ven_ari_dict)
    """
    try:
        sw_ven_ans_dict['juniper'] = sw_ven_juni_dict
    except:
        pass
    try:
        sw_ven_ans_dict['cisco'] = sw_ven_cis_dict
    except:
        pass
    try:
        sw_ven_ans_dict['arista'] = sw_ven_ari_dict
    except:
        pass


    print('This is the dict ', sw_ven_ans_dict)

    sw_ven_ans_dict = json.dumps(sw_ven_ans_dict)
    with open('sw_ven_ans_dict.json', 'w') as fl:
        fl.write(sw_ven_ans_dict)
    """
    ###Building Inventory for all switches#############
    for k,v in auth_dict.items():
        #########Building Inventory for Testbed#############
        if k == 'TB':
            #########Building Inventory for Juniper(junos) switch##########
            if v['sw_vendor'] == 'Juniper (junos)':
    """


    ################################################################################


    auth_dict = json.dumps(auth_dict)
    with open('tmp_auth_dict.json', 'w') as fl:
        fl.write(auth_dict)

    log_path_prelim = './logfiles/prelim_logfiles'
    log_path_final = './logfiles/final_logfiles'

    if path.exists(log_path_prelim) or path.exists(log_path_final):
        shutil.rmtree(log_path_prelim)
        shutil.rmtree(log_path_final)
    #    os.mkdir(log_path_prelim)
        os.mkdir(log_path_final)
        os.mkdir(log_path_prelim)

    return render_template("enter_so.j2")

####Clear existing log path and create new log path when starting new line item
@app.route('/enter_new_so', methods=["GET", "POST"])
def enter_new_so():
    os.remove('./tmp_opdata.json')

    log_path = './logfiles/prelim_logfiles'
    if path.exists(log_path):
        shutil.rmtree(log_path)
        os.mkdir(log_path)
    return render_template("enter_so.j2")

@app.route('/enter_so_process', methods=["GET", "POST"])
def enter_so_process():

    ########################################################################################################################
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
        tb_path = auth_dict['TB']['ansi_path']
        sw_vendor, username, passwd, hostname = auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass'], auth_dict['TB']['ip']
    if sw_vendor == 'juniper':
        env = Environment(loader=FileSystemLoader('.'))
        templ = env.get_template(tb_path +  "/gather_swmodel_datestamp.j2")

        with open(tb_path + "/gather_swmodel_datestamp.yml", "w") as fl:
            fl.write(templ.render(username=username, passwd=passwd))

        pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/gather_swmodel_datestamp.yml')
        res = pbrun.run()
    #############################################################################################################################
    so_num = {}
    so_num['num'] = request.args.get('so_num')
    so_num['hostname'] = hostname
    session['so_num'] = so_num

    return render_template("usr_input.j2")

@app.route('/usr_inp_process', methods=["GET", "POST"])
def usr_inp_process():
    ###############Dictionary to contain user input entered in home page##########################

    user_dict = {}
    user_dict['atten'] = request.args.get('atten')
    user_dict['int_slot'] = request.args.get('int_slot') ##getting the testbed optics location (e.g pic-slot 0 or 1) from input from user (usr_input.j2) and storing it in variable: "int_slot"##
    user_dict['ideal_op_id'] = request.args.get('ideal_op_id')

    if not user_dict['atten']==user_dict['int_slot']==user_dict['ideal_op_id']:
        user_dict = json.dumps(user_dict)
        with open("tmp_user_dict.json","w") as fl:
            fl.write(user_dict)

    ############call endpoint_mac_pull() in endpoint_pbrun.py module to run playbook to pull the Chassis MAC of switches used as endpoint
    endpoint_pbrun.endpoint_mac_pull()

    return render_template("opdata_chk.j2")

#optest_per_sn = {} ###Dictionary to hold optest results per interfaces with interface as the key

@app.route('/optic_validation', methods=["GET", "POST"])
def optic_validation():
    ###Dictionary to hold optest results per interfaces with interface as the key
    optest_per_sn = OrderedDict()
    session['optest_per_sn'] = optest_per_sn

    tstart = time.time()###########

    with open("tmp_user_dict.json") as fl:
        user_dict = ast.literal_eval(fl.read())

    print('This is user_dict: ', user_dict)
    int_slot = str(user_dict['int_slot']) ###storing the interface slot id entered by user in variable "int_slot"
    jun_idprom_cmd = "show chassis pic pic-slot " + int_slot + " fpc-slot 0" ####assgning juniper's idprom show command to variable: "jun_idprom_cmd" using the slot id entered by user in "usr_inp.j2"

    ######################################################new input###################################################################################################################
    ideal_op_id = user_dict['ideal_op_id']
########################################################NO need!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!for threading
    ##########################multiprocessing over idealoptic() and tb_intpull()############################################
    print(ideal_op_id,'\n',jun_idprom_cmd)
    funct1 = Process(target=idealoptic,args=(ideal_op_id, jun_idprom_cmd))
    funct1.start()
    funct2 = Process(target=tb_intpull)
    funct2.start()
    funct1.join()
    funct2.join()
#############################################################################################################################################################################


    ####################################################################################################
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    tb_path = auth_dict['TB']['ansi_path']
    sw_func, sw_vendor, username, passwd = auth_dict['TB']['sw_func'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass']
    """
    with open('./int_pull.json') as fl:
        int_lst = ast.literal_eval(fl.read().strip())
        int_lst = [re.sub(' +',' ',line) for line in int_lst]
        port_ids = []
        for line in int_lst:
            if line.split(" ")[0] != 'Port':
                port_ids.append(line.split(" ")[0])

        print(port_ids)

        ######################################################################

        env = Environment(loader=FileSystemLoader('.'))
        templ = env.get_template(tb_path + "/optical_data_pull_playb.j2")
        if sw_vendor == 'juniper':
            with open(tb_path + "/optical_data_pull_playb.yml", "w") as fl:
                fl.write(templ.render(port_ids=port_ids, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))

        if sw_vendor == 'cisco':
            temp = env.get_template(tb_path + "/templates/opdata_pull_temp.j2")

            #######Getting interface id from full port id#########################
            #ids = [port_id[port_id.rfind('/')+1:] for port_id in port_ids]
            id, ids = 0,[]
            for port_id in port_ids:
                ids.append(id)
                id+=1
            #########Create dictionary of port_ids to ids#######################
            cis_id = OrderedDict()
            for i in range(len(port_ids)):
                cis_id[port_ids[i]] = ids[i]

            print('This is:', cis_id)

            with open('/netauto/ansiblefiles/cisco_ios_ansiblefil/templates/opdata_pull.j2','w') as fl:
                fl.write(temp.render(ids=ids))
            with open(tb_path + "/optical_data_pull_playb.yml", "w") as fl:
                fl.write(templ.render(cis_id=cis_id, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))



            ########Define and run playbook object######################################################################
            pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/optical_data_pull_playb.yml')
            res = pbrun.run()
            testbed_viol_dict = optest_cisco_funcs.comp_testbed_ideal(ideal_op_id)
            print(testbed_viol_dict)

            ###########Tally up total number of errors to determine if violation has occured############################
            err_size = 0
            dom_err_cnt, idprom_err_cnt, inv_err_cnt = 0,0,0
            dom_err_loc, idprom_err_loc, inv_err_loc = [],{},[]
            dom_data, idprom_data, inv_data = [],{},[]
    #        try:
            for k,v in testbed_viol_dict.items():
                if k == 'dom_viol_dict':
                    if v['err_cnt'] != 0:
                        dom_err_loc,dom_err_cnt,dom_data = v['err_loc'],v['err_cnt'],v['data']
                if k == 'idprom_viol_dict':
                    for ind,val in v.items():
                        idprom_err_cnt += val['err_cnt']
                        if val['err_cnt'] > 0:
                            idprom_err_loc[ind] = val['err_loc']
                            idprom_data[ind] = val['data']
                if k == 'inv_viol_dict':
                    if v['err_cnt'] != 0:
                        inv_err_loc,inv_err_cnt,inv_data = v['err_loc'],v['err_cnt'],v['data']

            err_size = dom_err_cnt + inv_err_cnt + idprom_err_cnt
    #        except:
    #            return render_template("Eror")
            print('This is error count:', dom_err_cnt, idprom_err_cnt, inv_err_cnt)
            print('This is error location:', dom_err_loc, idprom_err_loc, inv_err_loc)
            print('This is error data:', dom_data, idprom_data, inv_data)

            if err_size == 0:
                return render_template("opdata_chk.j2",res = "Validation passed. No error found.")
            else:
                return render_template("cisco_opdata_viol_report.j2", err_size=err_size, dom_err_cnt=dom_err_cnt, inv_err_cnt=inv_err_cnt, idprom_err_cnt=idprom_err_cnt, dom_data=dom_data, idprom_data=idprom_data, inv_data=inv_data, dom_err_loc=dom_err_loc, idprom_err_loc=idprom_err_loc, inv_err_loc=inv_err_loc)
            """



    ####################################################################################################
    #try:
    env = Environment(loader=FileSystemLoader('.'))
    templ = env.get_template(tb_path + "/optical_data_pull_playb.j2")
    if sw_vendor == 'juniper':
        """
        env = Environment(loader=FileSystemLoader('.'))
        templ = env.get_template("./templates/idealop_playb.j2")

        with open(tb_path + "/idealop_playb.yml", "w") as fl:
            fl.write(templ.render(id_int=ideal_op, jun_idprom_cmd=jun_idprom_cmd, sw_func=sw_func, sw_vendor=sw_vendor))
        """
        ########################################Pulling Ideal optic optical test data###################
        with open('./resources/idealop.txt','r') as fl:
            idealop = fl.read()
        #######################################Pulling Optical data from all the optics in switch (without connection) to be compared with ideal optic selected#########
        env = Environment(loader=FileSystemLoader('.'))
        templ = env.get_template(tb_path + "/optical_data_pull_playb.j2")

        with open(tb_path + "/optical_data_pull_playb.yml", "w") as fl:
            fl.write(templ.render(jun_idprom_cmd=jun_idprom_cmd, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))

        ########Define and run playbook object######################################################################
        pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/optical_data_pull_playb.yml')
        res = pbrun.run()
        ###############################################################################################################

        ######pull opdata for all optics from txt file############
        with open("/netauto/opdata_pull.txt","r") as fl:
            opdata_pull = fl.read()
        ####DOM data extracted from "opdata_pull_lst"
        dom_opdata_lst = ast.literal_eval(opdata_pull.split("\n")[0])
        ####IDPROM data extracted from "opdata_pull_lst"
        idprom_opdata_lst = ast.literal_eval(opdata_pull.split("\n")[1])
        ####Inventory data extracted from "opdata_pull_lst"
        inv_opdata_lst = ast.literal_eval(opdata_pull.split("\n")[2])

        ########Extracting serial number from inventory data pulled from optics: 'inv_opdata_lst'
        inv_opdata_lst2 = [re.sub(' +',' ',i) for i in inv_opdata_lst]
        id_sn_dict = OrderedDict()

        for inv in inv_opdata_lst2:
            if 'Xcvr' in inv.strip():
                id_sn_dict[inv.strip().split(" ")[inv.strip().split(" ").index('Xcvr') + 1]] = inv.strip().split(" ")[-2]

        ######storing dictionary containing serial numbers of optics tested in a json file
        with open('tmp_sn_dict.json', 'w') as fl:
            json.dump(id_sn_dict, fl)
        """
        ######storing dictionary containing serial numbers of optics tested in a json file
        snfilename = 'tmp_sn_dict.json'
        if not path.isfile(snfilename):
            with open('tmp_sn_dict.json', 'w') as fl:
                json.dump(id_sn_dict, fl)
        else:
            with open('tmp_sn_dict.json') as fl:
                tmp_sn_dict = json.load(fl)
                tmp_sn_dict.update(id_sn_dict)
            with open('tmp_sn_dict.json', 'w') as fl:
                json.dump(tmp_sn_dict, fl)
        #session['id_sn_dict'] = id_sn_dict
        """
        ########################Comparing the ideal optics data with that of all the testbed optics################################################################
        testbed_viol_dict = optest_junos_funcs.comp_testbed_ideal(idealop, dom_opdata_lst, idprom_opdata_lst, inv_opdata_lst)
        print('This is testbed_viol_dict',testbed_viol_dict)
        err_size = 0
        idprom_err_cnt, dom_err_cnt, inv_err_cnt = 0,0,0
        idprom_err_loc, dom_err_loc, inv_err_loc = [],{},[]
        idprom_data, dom_data, inv_data = [],{},[]


        ###################Dictionary to carry Inventory and IDPROM data to "dom_test_stage" view function
        opdata = OrderedDict()
        opdata['idprom'] = idprom_opdata_lst
        opdata['inv'] = inv_opdata_lst
        with open("tmp_opdata.json", 'w') as fl:
            json.dump(opdata, fl)

        ###################################################################################################

    #        try:
        for k,v in testbed_viol_dict.items():
            if k == 'dom_viol_dict':
                for ind,val in v.items():
                    dom_err_cnt += val['err_cnt']
                    if val['err_cnt'] > 0:
                        dom_err_loc[ind] = val['err_loc']
                        dom_data[ind] = val['data']
            if k == 'idprom_viol_dict':
                if v['err_cnt'] != 0:
                    idprom_err_loc,idprom_err_cnt,idprom_data = v['err_loc'],v['err_cnt'],v['data']
            if k == 'inv_viol_dict':
                if v['err_cnt'] != 0:
                    inv_err_loc,inv_err_cnt,inv_data = v['err_loc'],v['err_cnt'],v['data']

        err_size = dom_err_cnt + inv_err_cnt + idprom_err_cnt
    #        except:
    #            return render_template("Eror")
        print('This is error count:', dom_err_cnt, idprom_err_cnt, inv_err_cnt)
        print('This is error location:', dom_err_loc, idprom_err_loc, inv_err_loc)
        print('This is error data:', dom_data, idprom_data, inv_data)

        if err_size == 0:
            return render_template("opdata_chk.j2",res = "Validation passed. No error found.")
        else:
            return render_template("juniper_opdata_viol_report.j2", err_size=err_size, dom_err_cnt=dom_err_cnt, inv_err_cnt=inv_err_cnt, idprom_err_cnt=idprom_err_cnt, dom_data=dom_data, idprom_data=idprom_data, inv_data=inv_data, dom_err_loc=dom_err_loc, idprom_err_loc=idprom_err_loc, inv_err_loc=inv_err_loc)


    if sw_vendor == 'cisco':
        with open('./int_pull.json') as fl:
            int_lst = ast.literal_eval(fl.read().strip())
            int_lst = [re.sub(' +',' ',line) for line in int_lst]
            port_ids = []
            for line in int_lst:
                if line.split(" ")[0] != 'Port':
                    port_ids.append(line.split(" ")[0])

            print(port_ids)
        temp = env.get_template(tb_path + "/templates/opdata_pull_temp.j2")

        #######Getting interface id from full port id#########################
        #ids = [port_id[port_id.rfind('/')+1:] for port_id in port_ids]
        id, ids = 0,[]
        for port_id in port_ids:
            ids.append(id)
            id+=1
        #########Create dictionary of port_ids to ids#######################
        cis_id = OrderedDict()
        for i in range(len(port_ids)):
            cis_id[port_ids[i]] = ids[i]

        print('This is:', cis_id)

        with open('/netauto/ansiblefiles/cisco_ios_ansiblefil/templates/opdata_pull.j2','w') as fl:
            fl.write(temp.render(ids=ids))
        with open(tb_path + "/optical_data_pull_playb.yml", "w") as fl:
            fl.write(templ.render(cis_id=cis_id, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))



        ########Define and run playbook object######################################################################
        pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/optical_data_pull_playb.yml')
        res = pbrun.run()
        testbed_viol_dict = optest_cisco_funcs.comp_testbed_ideal(ideal_op_id)
        print(testbed_viol_dict)

        ###########Tally up total number of errors to determine if violation has occured############################
        err_size = 0
        dom_err_cnt, idprom_err_cnt, inv_err_cnt = 0,0,0
        dom_err_loc, idprom_err_loc, inv_err_loc = [],{},[]
        dom_data, idprom_data, inv_data = [],{},[]
    #        try:
        for k,v in testbed_viol_dict.items():
            if k == 'dom_viol_dict':
                if v['err_cnt'] != 0:
                    dom_err_loc,dom_err_cnt,dom_data = v['err_loc'],v['err_cnt'],v['data']
            if k == 'idprom_viol_dict':
                for ind,val in v.items():
                    idprom_err_cnt += val['err_cnt']
                    if val['err_cnt'] > 0:
                        idprom_err_loc[ind] = val['err_loc']
                        idprom_data[ind] = val['data']
            if k == 'inv_viol_dict':
                if v['err_cnt'] != 0:
                    inv_err_loc,inv_err_cnt,inv_data = v['err_loc'],v['err_cnt'],v['data']

        err_size = dom_err_cnt + inv_err_cnt + idprom_err_cnt
    #        except:
    #            return render_template("Eror")
        print('This is error count:', dom_err_cnt, idprom_err_cnt, inv_err_cnt)
        print('This is error location:', dom_err_loc, idprom_err_loc, inv_err_loc)
        print('This is error data:', dom_data, idprom_data, inv_data)

        if err_size == 0:
            return render_template("opdata_chk.j2",res = "Validation passed. No error found.")
        else:
            return render_template("cisco_opdata_viol_report.j2", err_size=err_size, dom_err_cnt=dom_err_cnt, inv_err_cnt=inv_err_cnt, idprom_err_cnt=idprom_err_cnt, dom_data=dom_data, idprom_data=idprom_data, inv_data=inv_data, dom_err_loc=dom_err_loc, idprom_err_loc=idprom_err_loc, inv_err_loc=inv_err_loc)
    if sw_vendor == 'arista':
        with open('./int_pull.json') as fl:
            int_lst = ast.literal_eval(fl.read().strip())
            int_lst = [re.sub(' +',' ',line) for line in int_lst]
            port_ids = []
            for line in int_lst:
                if line.split(" ")[0] != 'Port':
                    port_ids.append(line.split(" ")[0])

        print(port_ids)

        with open(tb_path + "/optical_data_pull_playb.yml", "w") as fl:
            fl.write(templ.render(sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))

        ########Define and run playbook object######################################################################
        pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/optical_data_pull_playb.yml')
        res = pbrun.run()

        testbed_viol_dict = optest_arista_funcs.comp_testbed_ideal(ideal_op_id)

        ###########Tally up total number of errors to determine if violation has occured############################
        err_size = 0
        dom_err_cnt, idprom_err_cnt, inv_err_cnt = 0,0,0
        dom_err_loc, idprom_err_loc, inv_err_loc = [],[],[]
        dom_data, idprom_data, inv_data = [],[],[]
    #        try:
        for k,v in testbed_viol_dict.items():
            if k == 'dom_viol_dict':
                if v['err_cnt'] != 0:
                    dom_err_loc,dom_err_cnt,dom_data = v['err_loc'],v['err_cnt'],v['data']
            if k == 'idprom_viol_dict':
                if v['err_cnt'] > 0:
                    idprom_err_loc,idprom_err_cnt,idprom_data = v['err_loc'],v['err_cnt'],v['data']
            if k == 'inv_viol_dict':
                if v['err_cnt'] != 0:
                    inv_err_loc,inv_err_cnt,inv_data = v['err_loc'],v['err_cnt'],v['data']

        err_size = dom_err_cnt + inv_err_cnt + idprom_err_cnt
    #        except:
    #            return render_template("Eror")
        print('This is error count:', dom_err_cnt, idprom_err_cnt, inv_err_cnt)
        print('This is error location:', dom_err_loc, idprom_err_loc, inv_err_loc)
        print('This is error data:', dom_data, idprom_data, inv_data)

        if err_size == 0:
            return render_template("opdata_chk.j2",res = "Validation passed. No error found.")
        else:
            return render_template("arista_opdata_viol_report.j2", err_size=err_size, dom_err_cnt=dom_err_cnt, inv_err_cnt=inv_err_cnt, idprom_err_cnt=idprom_err_cnt, dom_data=dom_data, idprom_data=idprom_data, inv_data=inv_data, dom_err_loc=dom_err_loc, idprom_err_loc=idprom_err_loc, inv_err_loc=inv_err_loc)

    """
    except:
        opdata_viol_dict = {}
        err_cnt = 0
        return ('error!!!!!!!!')
    """
    """
    if sw_vendor == 'arista':
        with open('./int_pull.json') as fl:
            int_lst = ast.literal_eval(fl.read().strip())
            int_lst = [re.sub(' +',' ',line) for line in int_lst]
            port_ids = []
            for line in int_lst:
                if line.split(" ")[0] != 'Port':
                    port_ids.append(line.split(" ")[0])
        print(port_ids)
    temp = env.get_template(tb_path + "/templates/opdata_pull_temp.j2")

    #######Getting interface id from full port id#########################
    #ids = [port_id[port_id.rfind('/')+1:] for port_id in port_ids]
    id, ids = 0,[]
    for port_id in port_ids:
        ids.append(id)
        id+=1
    #########Create dictionary of port_ids to ids#######################
    cis_id = OrderedDict()
    for i in range(len(port_ids)):
        cis_id[port_ids[i]] = ids[i]

    print('This is:', cis_id)

    with open('/netauto/ansiblefiles/cisco_ios_ansiblefil/templates/opdata_pull.j2','w') as fl:
        fl.write(temp.render(ids=ids))
    with open(tb_path + "/optical_data_pull_playb.yml", "w") as fl:
        fl.write(templ.render(cis_id=cis_id, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))



    ########Define and run playbook object######################################################################
    pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/optical_data_pull_playb.yml')
    res = pbrun.run()
    testbed_viol_dict = optest_arista_funcs.comp_testbed_ideal(ideal_op_id)
    print(testbed_viol_dict)

    ###########Tally up total number of errors to determine if violation has occured############################
    err_size = 0
    dom_err_cnt, idprom_err_cnt, inv_err_cnt = 0,0,0
    dom_err_loc, idprom_err_loc, inv_err_loc = [],{},[]
    dom_data, idprom_data, inv_data = [],{},[]
#        try:
    for k,v in testbed_viol_dict.items():
        if k == 'dom_viol_dict':
            if v['err_cnt'] != 0:
                dom_err_loc,dom_err_cnt,dom_data = v['err_loc'],v['err_cnt'],v['data']
        if k == 'idprom_viol_dict':
            for ind,val in v.items():
                idprom_err_cnt += val['err_cnt']
                if val['err_cnt'] > 0:
                    idprom_err_loc[ind] = val['err_loc']
                    idprom_data[ind] = val['data']
        if k == 'inv_viol_dict':
            if v['err_cnt'] != 0:
                inv_err_loc,inv_err_cnt,inv_data = v['err_loc'],v['err_cnt'],v['data']

    err_size = dom_err_cnt + inv_err_cnt + idprom_err_cnt
#        except:
#            return render_template("Eror")
    print('This is error count:', dom_err_cnt, idprom_err_cnt, inv_err_cnt)
    print('This is error location:', dom_err_loc, idprom_err_loc, inv_err_loc)
    print('This is error data:', dom_data, idprom_data, inv_data)

    if err_size == 0:
        return render_template("opdata_chk.j2",res = "Validation passed. No error found.")
    else:
        return render_template("cisco_opdata_viol_report.j2", err_size=err_size, dom_err_cnt=dom_err_cnt, inv_err_cnt=inv_err_cnt, idprom_err_cnt=idprom_err_cnt, dom_data=dom_data, idprom_data=idprom_data, inv_data=inv_data, dom_err_loc=dom_err_loc, idprom_err_loc=idprom_err_loc, inv_err_loc=inv_err_loc)
    """
############################################################################################################################################
    return ('Optic not validated!!!')

@app.route('/dom_test_stage_disp', methods=["GET", "POST"])
def dom_test_stage_disp():
    return render_template("dom_test_stage.j2")

############change function name########################################
@app.route('/dom_test_stage', methods=["GET", "POST"])
def dom_test_stage():
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    tb_path = auth_dict['TB']['ansi_path']
    sw_func, sw_vendor, username, passwd = auth_dict['TB']['sw_func'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass']

    try:
        if sw_vendor == 'juniper':
            with open("tmp_opdata.json") as fl:
                opdata = json.load(fl)
            idprom_opdata_lst = opdata['idprom']
            inv_opdata_lst = opdata['inv']
            optest_junos_funcs.gen_oplogs(idprom_opdata_lst, inv_opdata_lst)
            return render_template("dom_test_stage.j2")
        if sw_vendor == 'cisco':
            with open("tmp_opdata.json") as fl:
                opdata = json.load(fl)
            idprom_opdata_lst = opdata['idprom']
            inv_opdata_lst = opdata['inv']
            optest_cisco_funcs.gen_oplogs(idprom_opdata_lst, inv_opdata_lst)
            return render_template("dom_test_stage.j2")
        if sw_vendor == 'arista':
            with open("tmp_opdata.json") as fl:
                opdata = json.load(fl)
            idprom_opdata_lst = opdata['idprom']
            inv_opdata_lst = opdata['inv']
            optest_arista_funcs.gen_oplogs(idprom_opdata_lst, inv_opdata_lst)
            return render_template("dom_test_stage.j2")
    except:
        return render_template("opdata_chk.j2",err_msg1 = "Optics not validated. Press ENTER to validate the optics then press CONTINUE.")

@app.route('/test_report', methods=["GET", "POST"])
def gen_optical_rep():
    ####################################################################################################
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    tb_path = auth_dict['TB']['ansi_path']

    sw_func, sw_vendor, username, passwd = auth_dict['TB']['sw_func'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass']
    """
    env = Environment(loader=FileSystemLoader('.'))
    templ = env.get_template("./templates/idealop_playb.j2")

    with open(tb_path + "/idealop_playb.yml", "w") as fl:
        fl.write(templ.render(id_int=ideal_op, jun_idprom_cmd=jun_idprom_cmd, sw_func=sw_func, sw_vendor=sw_vendor))
    """
    ###########################################################################
    ###########Pulling interface id "int_slot" entered by user
    with open("tmp_user_dict.json") as fl:
        user_dict = ast.literal_eval(fl.read())

    tstart_genopres = time.time()
    if sw_vendor == 'juniper':
        ###############################Call function run ansible playbook to pull interface data###########################
        tb_intpull()

        ###########################################Pulling a list of available interfaces from TB switch#################
        with open("./int_dat.txt","r") as fl:
            inter_dat = fl.read()

        #####Convert string of dictionary as read from file to the actual dictionary
        inter_lst = ast.literal_eval(inter_dat)

        ###########################List of interface ids pulled from optics in up/up state#######################
        interface_lst = optest_junos_funcs.int_extractor(inter_lst, user_dict['ideal_op_id'])
        #########################save interface_lst in text file###########################################
        with open("interface_lst_tmp.txt",'w') as fl:
            fl.write(str(interface_lst))

        print(interface_lst)
        int_lst_th = interface_lst

        ##########Call and define template to render interface data to create playbook for optical test#########
        env = Environment(loader=FileSystemLoader('.'))
        templ = env.get_template(tb_path + "/op_power_chk_playb.j2")

        power_chk_pb_path = Path(tb_path + "/op_power_chk_playb.yml")
        with open("temp_power_chk_pb_path",'w') as fl:
            fl.write(str(power_chk_pb_path))

        with open(power_chk_pb_path, "w") as fl:
            fl.write(templ.render(interface_lst=interface_lst, sw_vendor=sw_vendor, sw_func=sw_func, username=username, passwd=passwd))

        ##############use multiprocessing to run 'dom_pull_pbrun()' and 'optical_power_pull_endp()' in parallel#########################################
        funct1 = Process(target=dom_pull_pbrun)
        funct1.start()
        funct2 = Process(target=optical_power_pull_endp)
        funct2.start()
        funct1.join()
        funct2.join()

        ############################################open text file containing dom data and store in dictionary######################
        dom_pull_per_id = OrderedDict()
        with open('op_power_chk.json', 'r') as fl:
            dom_pull_data = ast.literal_eval(fl.read().strip())

        #id_sn_dict = session['id_sn_dict']

        if (len(interface_lst) == 1):
            dom_res_lst = dom_pull_data['stdout_lines']

            try:
                for port_id in interface_lst:
                    for val in dom_res_lst:
                        if port_id in val:
                            """
                            op_sn = id_sn_dict[port_id[port_id.rfind('/')+1:]]
                            #######add sn as a key and "dom_pull_per_id[port_id]" to dict
                            dom_res_lst.append(op_sn)
                            """
                            dom_pull_per_id[port_id] = dom_res_lst
            except:
                dom_pull_per_id[port_id] = []

        elif (len(interface_lst) > 1):
            dom_res_lst = dom_pull_data['results']
            try:
                for port_id in interface_lst:
                    for i in range(len(dom_res_lst)):
                        dom_per_id = dom_res_lst[i]['stdout_lines']
                        for val in dom_per_id:
                            if port_id in val:
                                """
                                op_sn = id_sn_dict[port_id[port_id.rfind('/')+1:]]
                                #######add sn as a key and "dom_pull_per_id[port_id]" to dict
                                dom_per_id.append(op_sn)
                                """
                                dom_pull_per_id[port_id] = dom_per_id
            except:
                dom_pull_per_id[port_id] = []


        """
        try:
            for port_id in interface_lst:
                for i in range(len(interface_lst)):
                    if port_id in dom_pull_data.strip('\n').split('\n')[i]:
                        dom_pull_per_id[port_id] = dom_pull_data.strip('\n').split('\n')[i]
        except:
            dom_pull_per_id[port_id] = []
        """
        print('This is dom_pull_per_id before thread: ',dom_pull_per_id)

        #######################################Dictionary to hold optical test result###############################
        optest_per_sn = session['optest_per_sn']

        ###########call function to generate optical test logs for DOM###########################################
        """
        for port_id, dom_lst in dom_pull_per_id.items():
            optest_junos_funcs.gen_oplogs_dom(dom_lst,port_id)
        """
        for port_id, dom_lst in dom_pull_per_id.items():
            optest_junos_funcs.gen_oplogs_dom(dom_lst)

        tstart_opanal = time.time()
        for i in range(len(int_lst_th)):
            int_lst_th[i] = Thread(target=optical_data_analysis, args=(int_lst_th[i],dom_pull_per_id[int_lst_th[i]],optest_per_sn, user_dict))
        for i in range(len(int_lst_th)):
            int_lst_th[i].start()
        for i in range(len(int_lst_th)):
            int_lst_th[i].join()
        tend_opanal = time.time()
        tend_genopres = time.time()
        print('Duration opanal: {:.4f}'.format(tend_opanal - tstart_opanal))
        print('Duration genopres: {:.4f}'.format(tend_genopres - tstart_genopres))

        """
        #########################get interface_lst from interface_lst text file###########################################
        with open("interface_lst_tmp.txt",'r') as fl:
            interface_lst = ast.literal_eval(fl.read())

        print(interface_lst)
        """
        ################function will combine the logs generated (during threading) for each port_id  in the interface_lst#####################
        #optest_junos_funcs.combine_gen_oplogs_dom(interface_lst)

        #################################sending the result of optical test: optest_per_sn to disp_optical_rep() for displaying###############
        optics_und_test = OrderedDict()

        print("this is optest_per_sn ", optest_per_sn)

    if sw_vendor == 'cisco':
        tb_intpull()
        ##############use multiprocessing to run 'dom_pull_pbrun()' and 'optical_power_pull_endp()' in parallel#########################################
        funct1 = Process(target=dom_pull_pbrun)
        funct1.start()
        funct2 = Process(target=optical_power_pull_endp)
        funct2.start()
        funct1.join()
        funct2.join()

        with open('int_pull.json') as fl:
            int_pull = ast.literal_eval(fl.read().strip())
            int_pull = [re.sub(' +',' ',i) for i in int_pull]
            int_lst = []
            for line in int_pull:
                if 'connected' == line.split(' ')[1]:
                    int_lst.append(line)
            interface_lst = [val.split(' ')[0] for val in int_lst]

        #########################save interface_lst in text file###########################################
        with open("interface_lst_tmp.txt",'w') as fl:
            fl.write(str(interface_lst))

        dom_pull_per_id = OrderedDict()
        with open('op_power_chk.json', 'r') as fl:
            dom_pull_data = fl.read()
        for i in range(dom_pull_data.count('\n\n')+1):
            dom_pull_per_id[interface_lst[i]] = ast.literal_eval(dom_pull_data.split('\n\n')[i])
        print(interface_lst)
        print(dom_pull_per_id)

        ##########generate dom logs for Cisco####################
        for port_id, dom_lst in dom_pull_per_id.items():
            optest_cisco_funcs.gen_oplogs_dom(dom_lst)

        int_lst_th = interface_lst
        optest_per_sn = session['optest_per_sn']
        tstart_opanal = time.time()
        for i in range(len(int_lst_th)):
            int_lst_th[i] = Thread(target=optical_data_analysis, args=(interface_lst[i],dom_pull_per_id[interface_lst[i]],optest_per_sn,user_dict))
        for i in range(len(int_lst_th)):
            int_lst_th[i].start()
        for i in range(len(int_lst_th)):
            int_lst_th[i].join()
        tend_opanal = time.time()
        tend_genopres = time.time()
        print('Duration opanal: {:.4f}'.format(tend_opanal - tstart_opanal))
        print('Duration genopres: {:.4f}'.format(tend_genopres - tstart_genopres))

        ################function will combine the logs generated (during threading) for each port_id  in the interface_lst#####################
        #optest_junos_funcs.combine_gen_oplogs_dom(interface_lst)

        #################################sending the result of optical test: optest_per_sn to disp_optical_rep() for displaying###############
        optics_und_test = OrderedDict()

        print("this is optest_per_sn ", optest_per_sn)

        ###############################################################

    if sw_vendor == 'arista':
        tb_intpull()
        ##############use multiprocessing to run 'dom_pull_pbrun()' and 'optical_power_pull_endp()' in parallel#########################################
        funct1 = Process(target=dom_pull_pbrun)
        funct1.start()
        funct2 = Process(target=optical_power_pull_endp)
        funct2.start()
        funct1.join()
        funct2.join()

        with open('int_pull.json') as fl:
            int_pull = ast.literal_eval(fl.read().strip())
            int_pull = [re.sub(' +',' ',i) for i in int_pull]
            int_lst = []
            for line in int_pull:
                if 'connected' == line.split(' ')[1]:
                    int_lst.append(line)
            interface_lst = [val.split(' ')[0] for val in int_lst]

        #########################save interface_lst in text file###########################################
        with open("interface_lst_tmp.txt",'w') as fl:
            fl.write(str(interface_lst))

        dom_pull_per_id = OrderedDict()
        with open('op_power_chk.json', 'r') as fl:
            dom_pull_data = fl.read()
        for i in range(dom_pull_data.count('\n\n')+1):
            dom_pull_per_id[interface_lst[i]] = ast.literal_eval(dom_pull_data.split('\n\n')[i].strip('\n'))
        print(interface_lst)
        print(dom_pull_per_id)

        ##########generate dom logs for Arista####################
        for port_id, dom_lst in dom_pull_per_id.items():
            optest_arista_funcs.gen_oplogs_dom(dom_lst)

        int_lst_th = interface_lst
        optest_per_sn = session['optest_per_sn']
        tstart_opanal = time.time()
        for i in range(len(int_lst_th)):
            int_lst_th[i] = Thread(target=optical_data_analysis, args=(interface_lst[i],dom_pull_per_id[interface_lst[i]],optest_per_sn,user_dict))
        for i in range(len(int_lst_th)):
            int_lst_th[i].start()
        for i in range(len(int_lst_th)):
            int_lst_th[i].join()
        tend_opanal = time.time()
        tend_genopres = time.time()
        print('Duration opanal: {:.4f}'.format(tend_opanal - tstart_opanal))
        print('Duration genopres: {:.4f}'.format(tend_genopres - tstart_genopres))

        ################function will combine the logs generated (during threading) for each port_id  in the interface_lst#####################
        #optest_junos_funcs.combine_gen_oplogs_dom(interface_lst)

    #################################sending the result of optical test: optest_per_sn to disp_optical_rep() for displaying###############
    optics_und_test = OrderedDict()
    #########################get interface_lst from interface_lst text file###########################################
    with open("interface_lst_tmp.txt",'r') as fl:
        interface_lst = ast.literal_eval(fl.read())

    print(interface_lst)
    print("this is optest_per_sn ", optest_per_sn)

    ###############################################################

#######################################################

    session['dict'] = optest_per_sn
    #############################if statement to trigger "dom_violation_report.j2" if False in "optest_per_sn"
    for k,v in optest_per_sn.items():
        for port_id in interface_lst:
            if k == port_id:
                optics_und_test[k] = v
    if "False" in str(optics_und_test):
        return render_template("dom_violation_report.j2", optest=optics_und_test)
    #########################################################################################################################################################################################################end of leave###############################################################
    """
    optest_tested_dict = OrderedDict()
    for k,v in optics_und_test.items():
        if not optics_und_test[k]:
            optest_tested_dict[k] = False
        else:
            optest_tested_dict[k] = True

    #optest_sn_list = list(optest_per_sn.keys())
    """
    return render_template("dom_test_stage.j2",optics_und_test=optics_und_test)

@app.route('/final_test_report', methods=["GET", "POST"])
def disp_optical_rep():
    try:
        optest_per_sn = session['dict']
        ############open all 3 optical test logs and combine them to create one log and output###############
        with open("./logfiles/prelim_logfiles/dom_log.txt",'r') as fl:
            dom_log = fl.read()
        with open("./logfiles/prelim_logfiles/idprom_log.txt",'r') as fl:
            idprom_log = fl.read()
        with open("./logfiles/prelim_logfiles/inv_log.txt",'r') as fl:
            inv_log = fl.read()

        oplog = ""
        oplog = dom_log + '\n' + idprom_log + '\n' + inv_log
        print(oplog)

        so_num_dict = session['so_num']
        so_num = so_num_dict['num']
        so_num = re.sub(' +', '', so_num)
        hostname = so_num_dict['hostname']

        ################Pull sw_model and ansible_date_time stamp from JSON file####################################
        try:
            with open('./sw_model.json') as fl:
                sw_model = fl.read().strip()
        except:
            sw_model = ''

        try:
            with open('./ansible_date_time.json') as fl:
                time_stamp = fl.read().strip()
        except:
            time_stamp = ''
        #############################################################################################################
        full_so_num = '{}_{}_ssh_{}_{}.txt'.format(so_num,sw_model,hostname,time_stamp)



        print(full_so_num)

        path_tofin_log = "./logfiles/final_logfiles/" + full_so_num
        session['path_tofin_log'] = path_tofin_log
        print('This is path_tofin_log',path_tofin_log)
        with open(path_tofin_log,'a') as fl:
            fl.write(oplog)
        return render_template("test_report.j2", optest=optest_per_sn)

    except:
        return render_template("dom_test_stage.j2", err_msg2="DOM of optics have not been tested. Click ENTER until all optics in the TB switch have been tested then click FINISH.")

@app.route('/optic_serial_num_disp', methods=["GET", "POST"])
def optic_serial_num_disp():
    with open('tmp_sn_dict.json') as fl:
        tmp_sn_dict = json.load(fl)
    return render_template("serial_list.j2", serial_lst=tmp_sn_dict.values())

@app.route('/logfiles', methods=["GET", "POST"])
def save_logfile():
    path_tofin_log = session['path_tofin_log']
    return send_file(path_tofin_log, as_attachment=True)

#########Run app########################
if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug=True)
